import datetime
import logging
import os.path
import re
import subprocess
import uuid
from collections import defaultdict, namedtuple
from functools import total_ordering
from urllib.parse import urlsplit, urlunsplit

import dateutil.parser
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile,
)
from django.urls import reverse
from django.utils.encoding import smart_bytes
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from langcodes import LANGUAGE_ALPHA3, Language, standardize_tag

from .cde_data_types import CDEDataTypes
from .registry_features import RegistryFeatures

logger = logging.getLogger(__name__)


class BadKeyError(Exception):
    pass


def get_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)[-1]


def get_form_section_code(delimited_key):
    return delimited_key.split(settings.FORM_SECTION_DELIMITER)


def mongo_key(form_name, section_code, cde_code):
    return settings.FORM_SECTION_DELIMITER.join(
        [form_name, section_code, cde_code]
    )


def mongo_key_from_models(form_model, section_model, cde_model):
    return mongo_key(form_model.name, section_model.code, cde_model.code)


def models_from_mongo_key(registry_model, delimited_key):
    from rdrf.models.definition.models import (
        CommonDataElement,
        RegistryForm,
        Section,
    )

    form_name, section_code, cde_code = get_form_section_code(delimited_key)
    try:
        form_model = RegistryForm.objects.get(
            name=form_name, registry=registry_model
        )
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


def dd_models_from_mongo_key(data_definitions, key):
    form_name, section_code, cde_code = get_form_section_code(key)
    if form_name != data_definitions.registry_form.name:
        raise BadKeyError()
    try:
        return (
            data_definitions.registry_form,
            data_definitions.sections_by_code[section_code],
            data_definitions.form_cdes[cde_code],
        )
    except KeyError:
        raise BadKeyError()


def is_delimited_key(s):
    try:
        parts = s.split(settings.FORM_SECTION_DELIMITER)
        if len(parts) == 3:
            return True
    except Exception:
        pass
    return False


def id_on_page(registry_form_model, section_model, cde_model):
    return mongo_key(
        registry_form_model.name, section_model.code, cde_model.code
    )


def de_camelcase(s):
    value = s[0].upper() + s[1:]
    chunks = re.findall("[A-Z][^A-Z]*", value)
    return " ".join(chunks)


class FormLink(object):
    def __init__(
        self,
        patient_id,
        registry,
        registry_form,
        selected=False,
        context_model=None,
    ):
        self.registry = registry
        self.patient_id = patient_id
        self.form = registry_form
        self.selected = selected
        self.context_model = context_model

    @property
    def url(self):
        if self.context_model is None:
            return reverse(
                "registry_form",
                args=(self.registry.code, self.form.pk, self.patient_id),
            )
        else:
            return reverse(
                "registry_form",
                args=(
                    self.registry.code,
                    self.form.pk,
                    self.patient_id,
                    self.context_model.id,
                ),
            )

    @property
    def text(self):
        return self.form.nice_name


def get_user(username):
    from registry.groups.models import CustomUser

    try:
        return CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return None


def get_users(usernames):
    return [
        x
        for x in [get_user(username) for username in usernames]
        if x is not None
    ]


def get_full_link(request, partial_link, login_link=False):
    if login_link:
        # return a redirect login
        # https://rdrf.ccgapps.com.au/ophg/login?next=/ophg/admin/
        login_url = "/account/login?next=" + partial_link
        return get_site_url(request, login_url)
    else:
        return get_site_url(request, partial_link)


def get_site_url(request, path="/"):
    # https://rdrf.ccgapps.com.au/ophg/admin/patients/patient/3/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # this part !
    return request.build_absolute_uri(path)


def location_name(registry_form, current_rdrf_context_model=None):
    form_display_name = registry_form.nice_name
    context_form_group = None
    if registry_form.registry.has_feature(RegistryFeatures.CONTEXTS):
        if current_rdrf_context_model is not None:
            patient_model = current_rdrf_context_model.content_object
            context_form_group = current_rdrf_context_model.context_form_group
            if context_form_group is not None:
                # context type name
                if context_form_group.naming_scheme == "C":
                    context_type_name = context_form_group.get_name_from_cde(
                        patient_model, current_rdrf_context_model
                    )
                    if context_form_group.supports_direct_linking:
                        return form_display_name + "/" + context_type_name
                else:
                    context_type_name = context_form_group.name

            else:
                context_type_name = ""

            name = (
                context_type_name
                if context_type_name
                else current_rdrf_context_model.display_name
            )
            s = "%s/%s" % (name, form_display_name)
        else:
            s = form_display_name
    else:
        s = form_display_name
    return s


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
        from rdrf.models.definition.models import Section

        section_model = Section.objects.get(code=code)
        return section_model.allow_multiple
    except Section.DoesNotExist:
        return False


def get_cde(code):
    from rdrf.models.definition.models import CommonDataElement

    return CommonDataElement.objects.filter(code=code).first()


def is_file_cde(code):
    cde = get_cde(code)
    return cde and cde.datatype == "file"


def is_multiple_file_cde(code):
    cde = get_cde(code)
    return cde and cde.datatype == "file" and cde.allow_multiple


def is_uploaded_file(value):
    return isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile))


def make_index_map(to_remove, count):
    """
    Returns a mapping from new_index -> old_index when indices
    `to_remove' are removed from a list of length `count'.
    For example:
      to_remove([1,3], 5) -> { 0:0, 1:2, 2:4 }
    """
    to_remove = set(to_remove)
    cut = [i for i in range(count) if i not in to_remove]
    return dict(list(zip(list(range(count)), cut)))


def get_form_links(
    user, patient_id, registry_model, context_model=None, current_form_name=""
):
    if user is None:
        return []
    patient_model = registry_model.patients.filter(pk=patient_id).first()
    if patient_model is None:
        return []

    context_form_group = (
        context_model.context_form_group if context_model else None
    )
    container_model = context_form_group or registry_model

    return [
        FormLink(
            patient_id,
            registry_model,
            form,
            selected=(form.name == current_form_name),
            context_model=context_model,
        )
        for form in container_model.forms
        if user.can_view(form)
        and form.applicable_to(patient_model, patient_in_registry_checked=True)
    ]


def forms_and_sections_containing_cde(registry_model, cde_model_to_find):
    results = []
    for form_model in registry_model.forms:
        for section_model in form_model.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code == cde_model_to_find.code:
                    results.append((form_model, section_model))
    return results


def consent_status_for_patient(registry_code, patient):
    from registry.patients.models import ConsentValue

    from rdrf.models.definition.models import ConsentSection

    values = ConsentValue.objects.filter(
        patient=patient, consent_question__section__registry__code=registry_code
    ).select_related("consent_question", "consent_question__section")

    answers = defaultdict(dict)
    sections = {}
    for v in values:
        section = v.consent_question.section
        sections[section.code] = section
        answers[section.code][v.consent_question.code] = v.answer

    if not values:
        # Special case for New Patients, who do NOT have ConsentValues yet
        sections = (
            s
            for s in ConsentSection.objects.filter(registry__code=registry_code)
            if s.applicable_to(patient)
        )
        for section in sections:
            if section.questions.exists():
                return False
        return True

    return all(
        sections[section_code].is_valid(section_answers)
        for section_code, section_answers in answers.items()
    )


def consent_status_for_patient_consent(
    registry, patient_id, consent_question_code
):
    from registry.patients.models import ConsentValue

    from rdrf.models.definition.models import ConsentQuestion

    consent_questions = ConsentQuestion.objects.filter(
        section__registry=registry, code=consent_question_code
    )
    consents_accepted_cnt = [
        ConsentValue.objects.filter(
            consent_question__id=consent_question.id,
            patient_id=patient_id,
            answer=True,
        ).count()
        for consent_question in consent_questions
    ]

    # Consent status is valid (True) if all relevant consent values are True
    # There must be at least one consent value for the patient that matches the consent question code supplied
    return len(consents_accepted_cnt) > 0 and all(consents_accepted_cnt)


def get_error_messages(forms):
    from rdrf.helpers.utils import de_camelcase

    messages = []

    def display(form_or_formset, field, error):
        form_name = form_or_formset.__class__.__name__.replace(
            "Form", ""
        ).replace("Set", "")
        qualifier = de_camelcase(form_name)
        if field:
            qualifier += f' {field.replace("_", " ")}'
        return f"{qualifier}: {error}"

    for form in forms:
        if hasattr(form, "non_form_errors"):
            for form_level_error in form.non_form_errors():
                messages.append(display(form, None, form_level_error))
        if isinstance(form._errors, list):
            for error_dict in form._errors:
                for field in error_dict:
                    messages.append(display(form, field, error_dict[field]))
        else:
            if form._errors is None:
                continue
            else:
                for field in form._errors:
                    for error in form._errors[field]:
                        field_label = form.fields[field].label
                        messages.append(display(form, field_label, error))
    results = list(map(strip_tags, messages))
    return results


def timed(func):
    logger = logging.getLogger(__name__)

    def wrapper(*args, **kwargs):
        a = datetime.datetime.now()
        result = func(*args, **kwargs)
        b = datetime.datetime.now()
        c = b - a
        func_name = func.__name__
        logger.debug("%s time = %s secs" % (func_name, c))
        return result

    return wrapper


def get_cde_value(
    form_model, section_model, cde_model, patient_record, form_index=None
):
    # should refactor code everywhere to use this func
    if patient_record is None:
        return None
    if form_index is not None:
        form_index = int(form_index)

    for form_dict in patient_record["forms"]:
        if form_dict["name"] == form_model.name:
            for section_dict in form_dict["sections"]:
                if section_dict["code"] == section_model.code:
                    if not section_dict["allow_multiple"]:
                        for cde_dict in section_dict["cdes"]:
                            if cde_dict["code"] == cde_model.code:
                                return cde_dict["value"]
                    else:
                        values = []
                        items = section_dict["cdes"]
                        for item in items:
                            for cde_dict in item:
                                if cde_dict["code"] == cde_model.code:
                                    values.append(cde_dict["value"])
                        if form_index is None:
                            return values
                        if form_index >= len(values):
                            return None
                        return values[form_index]


def get_display_value(cde_model, stored_value, permitted_values_map=None):
    if stored_value is None:
        return ""
    elif stored_value == "NaN":
        # the DataTable was not escaping this value and interpreting it as NaN
        return ":NaN"
    elif cde_model.pv_group:
        # if a range, return the display value
        if isinstance(stored_value, list):
            return stored_value
        if permitted_values_map:
            display_value = permitted_values_map.get(
                (stored_value, cde_model.pv_group_id), stored_value
            )
        else:
            display_value = cde_model.pv_group.cde_values_dict.get(
                stored_value, stored_value
            )
        return display_value
    elif cde_model.datatype.lower() == CDEDataTypes.DATE:
        try:
            return parse_iso_datetime(stored_value).date()
        except ValueError:
            return ""
    elif cde_model.datatype == CDEDataTypes.LOOKUP:
        from rdrf.forms.widgets.widgets import get_widget_class

        return get_widget_class(cde_model.widget_name).denormalized_value(
            stored_value
        )

    if stored_value == "NaN":
        # the DataTable was not escaping this value and interpreting it as NaN
        return ":NaN"

    return stored_value


def check_calculation(calculation):
    """
    Run a calculation javascript fragment through ADsafe to see
    whether it's suitable for running in users' browsers.
    Returns the empty string on success, otherwise an error message.
    """
    script = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "scripts", "check-calculation.js"
        )
    )
    try:
        p = subprocess.Popen(
            [script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output, _ = p.communicate(smart_bytes(calculation))
        if p.returncode != 0:
            return output.decode("utf-8", errors="replace")
    except OSError as e:
        logger.exception("Can't execute check-calculation.js")
        return "Couldn't execute %s: %s" % (script, e)
    return ""


def format_date(value):
    """
    Formats a date in Australian order, separated by hyphens, without
    leading zeroes.
    """
    return "{d.day}-{d.month}-{d.year}".format(d=value)


def parse_iso_date(s):
    "Opposite of datetime.datetime.isoformat()"
    return datetime.datetime.strptime(s, "%Y-%m-%d").date() if s else None


def parse_iso_datetime(s):
    "Opposite of datetime.date.isoformat()"
    return dateutil.parser.parse(s) if s else None


def wrap_uploaded_files(registry_code, post_files_data):
    from django.core.files.uploadedfile import UploadedFile

    from rdrf.forms.file_upload import FileUpload

    def wrap(key, value):
        if isinstance(value, UploadedFile):
            return FileUpload(
                registry_code,
                key,
                {"file_name": value.name, "django_file_id": 0},
            )
        else:
            return value

    return {
        key: wrap(key, value) for key, value in list(post_files_data.items())
    }


class Message:
    def __init__(self, text, tags=None):
        self.text = text
        self.tags = tags

    @staticmethod
    def success(text):
        return Message(text, tags="success")

    @staticmethod
    def info(text):
        return Message(text, tags="info")

    @staticmethod
    def warning(text):
        return Message(text, tags="warning")

    @staticmethod
    def danger(text):
        return Message(text, tags="danger")

    @staticmethod
    def error(text):
        return Message(text, tags="danger")

    def __repr__(self):
        return self.text


class TimeStripper(object):
    """
    This class exists to fix an error we introduced in the migration
    moving from Mongo to pure Django models with JSON fields ( "ClinicalData" objects.)
    CDE date values were converted  into iso strings including a time T substring.
    This was done recursively for the cdes and history collections
    """

    def __init__(self, dataset):
        self.dataset = (
            dataset  # queryset live , lists of data records for testing
        )
        # following fields used for testing
        self.test_mode = False
        self.converted_date_cdes = []
        self.date_cde_codes = []
        self.num_updates = 0  # actual conversions performed

    def forward(self):
        for thing in self.dataset:
            print("Checking ClinicalData object pk %s" % thing.pk)

            self.update(thing)
        print("Finished: Updated %s ClinicalData objects" % self.num_updates)

    def get_id(self, m):
        pk = m.pk

        if m.data:
            if "django_id" in m.data:
                django_id = m.data["django_id"]
            else:
                django_id = None

            if "django_model" in m.data:
                django_model = m.data["django_model"]
            else:
                django_model = None
            return "ClinicalData pk %s Django Model %s Django id %s" % (
                pk,
                django_model,
                django_id,
            )
        else:
            return "ClinicalData pk %s" % pk

    def munge_timestamp(self, datestring):
        if datestring is None:
            return datestring

        if "T" in datestring:
            t_index = datestring.index("T")
            return datestring[:t_index]
        else:
            return datestring

    def is_date_cde(self, cde_dict):
        code = cde_dict["code"]
        if self.test_mode:
            return code in self.date_cde_codes
        else:
            # not test mode
            from rdrf.models.definition.models import CommonDataElement

            try:
                cde_model = CommonDataElement.objects.get(code=code)
                value = cde_model.datatype == CDEDataTypes.DATE
                if value:
                    return value

            except CommonDataElement.DoesNotExist:
                print(
                    "Missing CDE Model! Data has code %s which does not exist on the site"
                    % code
                )

    def update_cde(self, cde):
        code = cde.get("code", None)
        if not code:
            print("No code in cde dict?? - not updating")
            return
        old_datestring = cde["value"]
        new_datestring = self.munge_timestamp(old_datestring)
        if new_datestring != old_datestring:
            cde["value"] = new_datestring
            if self.test_mode:
                self.converted_date_cdes.append(cde["value"])
            print(
                "Date CDE %s %s --> %s" % (code, old_datestring, new_datestring)
            )

            return True

    def update(self, m):
        updated = False
        ident = self.get_id(m)
        if m.data:
            updated = self.munge_data(m.data)
            if updated:
                try:
                    m.save()
                    print("%s saved OK" % ident)
                    self.num_updates += 1
                except Exception as ex:
                    print(
                        "Error saving ClinicalData object %s after updating: %s"
                        % (ident, ex)
                    )
                    raise  # rollback

    def munge_data(self, data):
        updated = 0
        if "forms" in data:
            for form in data["forms"]:
                if "sections" in form:
                    for section in form["sections"]:
                        if not section["allow_multiple"]:
                            if "cdes" in section:
                                for cde in section["cdes"]:
                                    if self.is_date_cde(cde):
                                        if self.update_cde(cde):
                                            updated += 1
                        else:
                            items = section["cdes"]
                            for item in items:
                                for cde in item:
                                    if self.is_date_cde(cde):
                                        if self.update_cde(cde):
                                            updated += 1

        return updated > 0


class HistoryTimeStripper(TimeStripper):
    def munge_data(self, data):
        # History embeds the full forms dictionary in the record key
        return super().munge_data(data["record"])


# Python 3.5 doesn't raises run time error when lists which contain None values are sorted
# see stackover flow
# http://stackoverflow.com/questions/12971631/sorting-list-by-an-attribute-that-can-be-none
@total_ordering
class MinType(object):
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return self is other


def get_field_from_model(model_path):
    # model_path looks like:  model/ConsentSection/23/information_text
    # model must be in rdrf.models
    from django.apps import apps

    try:
        parts = model_path.split("/")
        model_name = parts[1]
        pk = int(parts[2])
        field = parts[3]
        model_class = apps.get_model("rdrf", model_name)
        model_instance = model_class.objects.get(pk=pk)
        value = getattr(model_instance, field)
        return value
    except Exception as ex:
        logger.exception(
            "Error retrieving value from model_path %s: %s" % (model_path, ex)
        )
        return


def get_registry_definition_value(field_path):
    # find a value in a registry definition
    # model/<ModelName>/<pk>/<fieldname> - delegated to get_field_from_model above

    if field_path.startswith("model/"):
        return get_field_from_model(field_path)
    else:
        raise ValueError("Unsupported fieldpath: %s" % field_path)


def trans_file(request, doc_name_with_out_language):
    from django.conf import settings

    default_language = "EN"
    languages = [pair[0].upper() for pair in settings.LANGUAGES]
    language = request.META.get("HTTP_ACCEPT_LANGUAGE", default_language)
    if language != default_language:
        if language in languages:
            new_file_name = language + "_" + doc_name_with_out_language
            return new_file_name

    return doc_name_with_out_language


LanguageInfo = namedtuple("Language", ["code", "name"])


def get_supported_languages():
    return [LanguageInfo(pair[0], pair[1]) for pair in settings.LANGUAGES]


def get_all_language_codes():
    languages_in_settings = dict(settings.ALL_LANGUAGES)
    language_codes = set(languages_in_settings.keys())
    language_codes_simple = set(s.split("-")[0] for s in language_codes)
    extra_language_codes = set(LANGUAGE_ALPHA3.keys()).difference(
        language_codes_simple
    )
    language_codes.update(extra_language_codes)
    languages = []
    if "pseudo" in language_codes:
        languages = [LanguageInfo("pseudo", "pseudo")]
        language_codes.remove("pseudo")
    sorted_language_codes = sorted(
        set(standardize_tag(subtag) for subtag in language_codes)
    )
    for subtag in sorted_language_codes:
        alpha3_language_name = Language.get(subtag)
        if alpha3_language_name.is_valid():
            languages.append(
                LanguageInfo(
                    subtag,
                    languages_in_settings.get(
                        subtag, alpha3_language_name.autonym()
                    ),
                )
            )

    return languages


def applicable_forms(registry_model, patient_model):
    patient_type = patient_model.patient_type or "default"
    return applicable_forms_for_patient_type(registry_model, patient_type)


def applicable_forms_for_patient_type(registry_model, patient_type):
    patient_type_map = registry_model.metadata.get("patient_types")
    # type map looks like:
    # { "carrier": { "name": "Female Carrier", "forms": ["CarrierForm"]} }

    all_forms = registry_model.forms

    if patient_type_map is None:
        return all_forms

    if patient_type not in patient_type_map:
        return []

    applicable_form_names = set(patient_type_map[patient_type].get("forms"))
    if not applicable_form_names:
        return all_forms
    return [form for form in all_forms if form.name in applicable_form_names]


def patients_family_in_users_groups(patient, user):
    patient_wgs = set([wg.id for wg in patient.working_groups.all()])
    user_wgs = set([wg.id for wg in user.working_groups.all()])
    if not user_wgs.intersection(patient_wgs):
        family_wgs = set([wg.id for wg in patient.family.working_groups])
        return user_wgs.intersection(family_wgs)


def consent_check(registry_model, user_model, patient_model, capability):
    # if there are any consent rules for user's group , perform the check
    # if any fail , fail, otherwise pass (return True)
    from rdrf.models.definition.models import ConsentRule

    if not registry_model.has_feature(RegistryFeatures.CONSENT_CHECKS):
        return True

    if user_model.is_superuser:
        return True
    for user_group in user_model.groups.all():
        for consent_rule in ConsentRule.objects.filter(
            registry=registry_model,
            capability=capability,
            user_group=user_group,
            enabled=True,
        ):
            consent_answer = patient_model.get_consent(
                consent_rule.consent_question
            )
            if not consent_answer:
                return False

    return True


def get_full_path(registry_model, cde_code):
    """
    Return triple of form name, section code and cde code for a unique code
    """
    triples = []

    for form_model in registry_model.forms:
        for section_model in form_model.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code == cde_code:
                    triples.append(
                        (form_model.name, section_model.code, cde_code)
                    )
    if len(triples) != 1:
        raise ValueError(
            "cde code %s is not unique or not used by registry %s"
            % (cde_code, registry_model.code)
        )

    return triples[0]


def generate_token():
    return str(uuid.uuid4())


def get_site(request=None):
    if request:
        from django.contrib.sites.shortcuts import get_current_site

        return get_current_site(request)
    else:
        from django.contrib.sites.models import Site

        try:
            domain = Site.objects.first().domain
            if domain.startswith("localhost"):
                return "http://localhost:8000"
            else:
                return "https://" + domain

        except Site.DoesNotExist:
            return "http://localhost:8000"


def get_preferred_languages():
    # Registration allows choice of preferred language
    # But we allow different sites to expose different values
    # over time without code change via env --> settings

    # The default list is english only which we don't bother to show
    languages = get_supported_languages()

    if len(languages) == 1 and languages[0].code == "en":
        return []
    else:
        return languages


def is_authorised(user, patient_model):
    if user.is_superuser:
        return True
    from registry.patients.models import ParentGuardian

    # is the given user allowed to see this patient
    # patient IS user:
    if patient_model.user and patient_model.user.id == user.id:
        return True
    # user is parent of patient
    try:
        pg = ParentGuardian.objects.get(user=user)
        if pg.user and pg.user.id == user.id:
            if patient_model.id in [p.id for p in pg.children]:
                return True
    except ParentGuardian.DoesNotExist:
        pass

    # otherwise, is the user in (some of) the same working group(s)

    user_wgs = set([wg.id for wg in user.working_groups.all()])
    patient_wgs = set([wg.id for wg in patient_model.working_groups.all()])
    common = user_wgs.intersection(patient_wgs)
    if common and not user.is_parent:
        return True

    return False


def check_suspicious_sql(sql_query, user):
    sql_query_lowercase = " ".join(sql_query.lower().split())
    security_errors = []
    if any(
        sql_command in sql_query_lowercase
        for sql_command in ["drop", "delete", "update"]
    ):
        logger.warning(
            f"User {user} tries to write/validate a suspicious SQL: {sql_query_lowercase}"
        )
        security_errors.append(
            "The SQL query must not contain any of these keywords: DROP, DELETE, UPDATE"
        )
    return security_errors


def is_alphanumeric(input_str):
    return re.match(r"^[a-zA-Z0-9]*$", input_str) is not None


def validate_abbreviated_name(value):
    if re.match(r"^[A-Za-z0-9\s-]+$", value) is None:
        logger.info(f"validation failed for {value}")
        raise ValidationError(
            _(
                "Abbreviated name contains invalid characters. Accepted characters: Alphanumeric, spaces and dashes."
            )
        )


def validate_file_extension_format(value):
    if re.match(r"^\.[^.]+$", value) is None:
        raise ValidationError(
            _(
                "File extension "
                "is invalid. "
                "File extension should begin with a period followed by some characters e.g: .pdf"
            )
        )


def make_full_url(relative_url):
    splitted = urlsplit(relative_url)
    domain = Site.objects.get_current().domain.rstrip("/")
    scheme = (
        "https"
        if domain not in ["localhost:8000", "serverundertest:8000"]
        else "http"
    )
    augmented = splitted._replace(scheme=scheme, netloc=domain)
    return urlunsplit(augmented)


def silk_profile(*args, **kwargs):
    if settings.PROFILING:
        from silk.profiling.profiler import silk_profile

        return silk_profile(*args, **kwargs)
    return lambda x: x
