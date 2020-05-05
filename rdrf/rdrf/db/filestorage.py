import botocore
from collections import namedtuple
import logging
import re

from django.conf import settings
from django.core.files.storage import default_storage

from storages.backends.s3boto3 import S3Boto3Storage

from rdrf.models.definition.models import Registry, CDEFile
from rdrf.helpers.utils import models_from_mongo_key

logger = logging.getLogger(__name__)

__all__ = ["get_id", "delete_file_wrapper", "get_file",
           "store_file", "store_file_by_key", "StorageFileInfo"]


StorageFileInfo = namedtuple('StorageFileInfo', 'item filename uploaded_by patient', defaults=(None, None, None, None))
EMPTY_FILE_INFO = StorageFileInfo()


def get_id(value):
    if isinstance(value, dict):
        return value.get("django_file_id")
    return None


def delete_file_wrapper(file_ref):
    django_file_id = file_ref.get("django_file_id")
    if django_file_id is not None:
        try:
            CDEFile.objects.get(id=django_file_id).delete()
        except CDEFile.DoesNotExist:
            logger.warning("Tried to delete CDEFile id=%s which doesn't exist" % django_file_id)
        except Exception:
            logger.exception("Couldn't delete CDEFile id=%s" % django_file_id)
        return django_file_id

    return None


def store_file(registry_code, uploaded_by, patient, cde_code, file_obj, form_name=None, section_code=None):
    cde_file = CDEFile(registry_code=registry_code,
                       uploaded_by=uploaded_by,
                       patient=patient,
                       form_name=form_name,
                       section_code=section_code,
                       cde_code=cde_code,
                       item=file_obj,
                       filename=file_obj.name)
    cde_file.save()

    return {
        "django_file_id": cde_file.id,
        "file_name": file_obj.name
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
        return StorageFileInfo(item=cde_file.item, filename=cde_file.filename, uploaded_by=cde_file.uploaded_by, patient=cde_file.patient)
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
        This method isn't part of the Storage API, it is an extra method added by us.
        '''
        try:
            name = self._encode_name(self._normalize_name(self._clean_name(name)))
            response = self.connection.meta.client.get_object_tagging(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=name)
            return {el['Key']: el['Value'] for el in response['TagSet']}
        except botocore.exceptions.ClientError as tce:
            if tce.response['Error']['Code'] == 'NoSuchKey':
                pass
            else:
                raise tce
        return {}


class VirusScanStatus:
    SCANNING = 'scanning'
    CLEAN = 'clean'
    INFECTED = 'infected'


class S3VirusChecker:

    def __init__(self, storage):
        self.storage = storage

    def check(self, name):
        tags = self.storage.get_tags(name)
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
