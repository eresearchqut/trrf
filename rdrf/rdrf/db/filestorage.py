from collections import namedtuple
import logging
import re
from rdrf.models.definition.models import Registry, CDEFile
from rdrf.helpers.utils import models_from_mongo_key

logger = logging.getLogger(__name__)

__all__ = ["get_id", "delete_file_wrapper", "get_file",
           "store_file", "store_file_by_key", "StorageFileInfo"]


StorageFileInfo = namedtuple('StorageFileInfo', 'item filename uploaded_by patient')


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
        return StorageFileInfo(item=None, filename=None, uploaded_by=None, patient=None)
