from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction

import logging
import re

logger = logging.getLogger("registry_log")


class BadKeyError(Exception):
    pass

def mongo_db_name(registry):
    return settings.MONGO_DB_PREFIX + registry


def mongo_db_name_reg_id(registry_id):
    from models import Registry
    reg = Registry.objects.get(id=registry_id)
    return settings.MONGO_DB_PREFIX + reg.code


def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]


def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)


def mongo_key(form_name, section_code, cde_code):
    return settings.FORM_SECTION_DELIMITER.join([form_name, section_code, cde_code])


def mongo_key_from_models(form_model, section_model, cde_model):
    return mongo_key(form_model.name, section_model.code, cde_model.code)


def models_from_mongo_key(registry_model, delimited_key):
    from rdrf.models import RegistryForm, Section, CommonDataElement
    form_name, section_code, cde_code = get_form_section_code(delimited_key)
    try:
        form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
    except RegistryForm.DoesNotExist:
        raise BadKeyError()

    try:
        section_model = Section.objects.get(code=section_code)
    except Section.DoesNotExist:
        raise BadKeyError()

    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
    except CommonDataElement.DoesNotExist:
        raise BadKeyError()

    return form_model, section_model, cde_model


def is_delimited_key(s):
    try:
        parts = s.split(settings.FORM_SECTION_DELIMITER)
        if len(parts) == 3:
            return True
    except Exception:
        pass
    return False



def id_on_page(registry_form_model, section_model, cde_model):
    return mongo_key(registry_form_model.name, section_model.code, cde_model.code)


def de_camelcase(s):
    value = s[0].upper() + s[1:]
    chunks = re.findall('[A-Z][^A-Z]*', value)
    return " ".join(chunks)


class FormLink(object):

    def __init__(self, patient_id, registry, registry_form, selected=False):
        self.registry = registry
        self.patient_id = patient_id
        self.form = registry_form
        self.selected = selected

    @property
    def url(self):
        from django.core.urlresolvers import reverse
        return reverse(
            'registry_form',
            args=(
                self.registry.code,
                self.form.pk,
                self.patient_id))

    @property
    def text(self):
        return de_camelcase(self.form.name)


def get_user(username):
    from registry.groups.models import CustomUser
    try:
        return CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return None


def get_users(usernames):
    return filter(lambda x: x is not None, [get_user(username) for username in usernames])


def has_feature(feature_name):
    if settings.FEATURES == "*":
        return True
    return feature_name in settings.FEATURES  # e.g. [ 'email_notification', 'adjudication' ]


def requires_feature(feature_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if has_feature(feature_name):
                return func(*args, **kwargs)
            else:
                logger.info(
                    "%s will not be run with args %s kwargs %s as the site lacks feature %s" %
                    (func.__name__, args, kwargs, feature_name))
        return wrapper
    return decorator


def get_full_link(request, partial_link, login_link=False):
    if login_link:
        # return a redirect login    https://rdrf.ccgapps.com.au/ophg/login?next=/ophg/admin/
        login_url = "/login?next=" + partial_link
        return get_site_url(request, login_url)
    else:
        return get_site_url(request, partial_link)


def get_site_url(request, path="/"):
    # https://rdrf.ccgapps.com.au/ophg/admin/patients/patient/3/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # this part !
    return request.build_absolute_uri(path)


def location_name(registry_form):
    return de_camelcase(registry_form.name)


def cached(func):
    d = {}

    def wrapped(*args, **kwargs):
        key = str("%s %s" % (args, kwargs))
        if key in d:
            return d[key]
        else:
            d[key] = func(*args, **kwargs)
            return d[key]

    return wrapped


def is_multisection(code):
    try:
        from rdrf.models import Section
        section_model = Section.objects.get(code=code)
        return section_model.allow_multiple
    except Section.DoesNotExist:
        return False


def is_file_cde(code):
    from rdrf.models import CommonDataElement
    try:
        cde = CommonDataElement.objects.get(code=code)
        if cde.datatype == 'file':
            return True
    except Exception:
        pass
    return False


def is_uploaded_file(value):
    from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
    return isinstance(value, InMemoryUploadedFile) or isinstance(value, TemporaryUploadedFile)


def make_index_map(index_actions_list):
    # index_actions_list looks like [1,0,1,0,1]
    # 1 means that this item in the list was not deleted
    # 0 means that item in the list was deleted
    # we return a map mapping the positions of the 1s ( kept items)
    # to original indices - this allows us to retriebve data from an item
    # depsite re-ordering\
    # index map in example is {0: 0, 1: 2, 2: 4}

    m = {}
    new_index = 0
    for original_index, i in enumerate(index_actions_list):
        if i == 1:
            m[new_index] = original_index
            new_index += 1
    return m


def is_gridfs_file_wrapper(value):
    return isinstance(value, dict) and "griffs_file_id" in value

def create_permission(app_label, model, code_name, name):
    content_type = ContentType.objects.get(app_label=app_label, model=model)
    
    try:
        with transaction.atomic():
            Permission.objects.create(codename=code_name, name=name, content_type=content_type)
    except IntegrityError:
        pass
