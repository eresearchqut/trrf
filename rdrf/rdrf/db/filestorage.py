import uuid

import botocore
from collections import namedtuple
from enum import Enum
import logging
import magic
import re

from django.conf import settings
from django.core.files.storage import default_storage

from storages.backends.s3boto3 import S3Boto3Storage

from rdrf.helpers.utils import models_from_mongo_key
from rdrf.models.definition.models import Registry, CDEFile

logger = logging.getLogger(__name__)

__all__ = ["get_id", "delete_file_wrapper", "get_file", "create_filestorage", "StorageFileInfo"]


StorageFileInfo = namedtuple('StorageFileInfo', 'item filename uploaded_by patient mime_type', defaults=(None, None, None, None, None))
EMPTY_FILE_INFO = StorageFileInfo()


FileStorageEventType = Enum("FileStorageEventType", "UPLOADED DELETED")
FileStorageEvent = namedtuple("FileStorageEvent", "type cde_file")


class ActionLoggingFileStorage:
    def __init__(self):
        self.actions = []

    @property
    def uploads(self):
        return [action for action_type, action in self.actions if action_type == FileStorageEventType.UPLOADED]

    def upload_to_cde_file(self, upload):
        return CDEFile.objects.filter(pk=upload.get('django_file_id')).first()

    def log_upload(self, upload):
        self.actions.append(FileStorageEvent(FileStorageEventType.UPLOADED, self.upload_to_cde_file(upload)))

    def store_file_by_key(self, registry_code, patient_record, uploaded_by, key, value):
        upload = store_file_by_key(registry_code, patient_record, uploaded_by, key, value)
        self.log_upload(upload)
        return upload

    def store_file(self, registry_code, uploaded_by, patient, cde_code, file_obj, form_name=None, section_code=None):
        upload = store_file(registry_code, uploaded_by, patient, cde_code, file_obj, form_name, section_code)
        self.log_upload(upload)
        return upload

    def delete_file(self, file_ref):
        cde_file = delete_file_wrapper(file_ref)
        self.actions.append(FileStorageEvent(FileStorageEventType.DELETED, cde_file))


def create_filestorage():
    return ActionLoggingFileStorage()


def get_id(value):
    if isinstance(value, dict):
        return value.get("django_file_id")
    return None


def delete_file_wrapper(file_ref):
    django_file_id = file_ref.get("django_file_id")
    if django_file_id is not None:
        try:
            cde_file = CDEFile.objects.get(id=django_file_id)
            cde_file.delete()
            return cde_file
        except CDEFile.DoesNotExist:
            logger.warning("Tried to delete CDEFile id=%s which doesn't exist" % django_file_id)
        except Exception:
            logger.exception("Couldn't delete CDEFile id=%s" % django_file_id)

    return None


def store_file(registry_code, uploaded_by, patient, cde_code, file_obj, form_name=None, section_code=None):
    mime_type = magic.from_buffer(file_obj.read(2048), mime=True)
    file_obj.seek(0)
    storage_filename = str(uuid.uuid4())
    original_filename = file_obj.name
    cde_file = CDEFile(registry_code=registry_code,
                       uploaded_by=uploaded_by,
                       patient=patient,
                       form_name=form_name,
                       section_code=section_code,
                       cde_code=cde_code,
                       item=file_obj,
                       original_filename=original_filename,
                       filename=storage_filename,
                       mime_type=mime_type)
    cde_file.save()

    return {
        "django_file_id": cde_file.id,
        "file_name": original_filename
    }


def store_file_by_key(registry_code, patient_record, user, key, file_obj):
    registry = Registry.objects.get(code=registry_code)
    form, section, cde = models_from_mongo_key(registry, key)
    user_to_store = user
    if not user and patient_record:
        user_to_store = patient_record.user
    return store_file(registry_code,
                      user_to_store,
                      patient_record,
                      cde.code,
                      file_obj,
                      form.name,
                      section.code)


oid_pat = re.compile(r"[0-9A-F]{24}", re.I)


def get_file(file_id):
    try:
        cde_file = CDEFile.objects.get(id=file_id)
        return StorageFileInfo(
            item=cde_file.item, filename=cde_file.filename,
            uploaded_by=cde_file.uploaded_by, patient=cde_file.patient,
            mime_type=cde_file.mime_type
        )
    except CDEFile.DoesNotExist:
        return EMPTY_FILE_INFO
    except IOError:
        return EMPTY_FILE_INFO


class CustomS3Storage(S3Boto3Storage):

    def open(self, file_name, mode='rb'):
        try:
            return super().open(file_name, mode)
        except botocore.exceptions.ClientError as ex:
            if ex.response['Error']['Code'] == '403':
                raise PermissionError
            else:
                raise ex

    def get_tags(self, name):
        '''
        Returns dict of tags key/values of an S3 object.
        Empty dict is returned if the object is in scanning state, None if it does not exist
        This method isn't part of the Storage API, it is an extra method added by us.
        '''
        try:
            name = self._normalize_name(self._clean_name(name))
            response = self.connection.meta.client.get_object_tagging(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=name)
            return {el['Key']: el['Value'] for el in response['TagSet']}
        except botocore.exceptions.ClientError as tce:
            if tce.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                raise tce
        return {}

    def exists(self, name):
        '''
        Determines whether a file exists in the bucket already, and thus needs a new file name.

        This method overrides the existing method because of the way we do virus scanning on uploaded files.
        Files uploaded with virus scanning enabled will return 403 errors until they are cleared.
        In the original method, 403 and 404 errors are treated as missing files, which means that currently-scanning
        files can be overwritten if a second file with the same name is uploaded.
        '''

        name = self._normalize_name(self._clean_name(name))
        try:
            self.connection.meta.client.head_object(Bucket=self.bucket_name, Key=name)
            return True
        except botocore.exceptions.ClientError as e:
            code = e.response['Error']['Code']
            if code == "403":
                return True
            elif code == "404":
                return False
            else:
                raise e


class VirusScanStatus:
    SCANNING = 'scanning'
    CLEAN = 'clean'
    INFECTED = 'infected'
    NOT_FOUND = 'not found'


class S3VirusChecker:

    def __init__(self, storage):
        self.storage = storage

    def check(self, name):
        tags = self.storage.get_tags(name)
        if tags is None:
            return VirusScanStatus.NOT_FOUND
        status = tags.get('av-status', '')
        if not status:
            return VirusScanStatus.SCANNING
        elif status == 'INFECTED':
            return VirusScanStatus.INFECTED
        return VirusScanStatus.CLEAN


def virus_checker_result(filename):
    if not settings.VIRUS_CHECKING_ENABLED:
        return VirusScanStatus.CLEAN
    if isinstance(default_storage, CustomS3Storage):
        return S3VirusChecker(default_storage).check(filename)
    return VirusScanStatus.CLEAN
