import datetime
import json
import logging
import random
from collections import namedtuple
from functools import reduce
from operator import attrgetter

import pycountry
from django.contrib.postgres.fields import ArrayField
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.files.storage import DefaultStorage
from django.db import models
from django.db.models import Q
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
)
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

import registry.groups.models
from rdrf.db.dynamic_data import DynamicDataWrapper
from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import (
    ClinicalData,
    ConsentQuestion,
    DataDefinitions,
    LongitudinalFollowup,
    Registry,
    Section,
)
from rdrf.models.workflow_models import ClinicianSignupRequest
from rdrf.services.io.notifications.email_notification import (
    process_notification,
)
from rdrf.services.io.notifications.file_notifications import (
    handle_file_notifications,
)
from registry.groups.models import CustomUser
from registry.utils import get_registries, get_working_groups, stripspaces

from .constants import PatientState

logger = logging.getLogger(__name__)

_6MONTHS_IN_DAYS = 183


class State(models.Model):
    short_name = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=30)
    country_code = models.CharField(max_length=30, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Family(object):
    def __init__(self, patient):
        if patient.is_index:
            self.index = patient
        else:
            self.index = patient.as_a_relative.patient

        self.relatives = [pr for pr in self.index.relatives.all()]

    @property
    def working_groups(self):
        # all the working groups this family spans
        # we need this for checking security
        wgs = [wg for wg in self.index.working_groups.all()]
        wgs = wgs + [
            wg
            for pr in self.relatives
            for wg in pr.relative_patient.working_groups.all()
            if pr.relative_patient
        ]
        return wgs


class Doctor(models.Model):
    SEX_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))

    # TODO: Is it possible for one doctor to work with multiple working groups?
    title = models.CharField(max_length=4, blank=True, null=True)
    family_name = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Family/Last name")
    )
    given_names = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Given/First names")
    )
    sex = models.CharField(
        max_length=1, choices=SEX_CHOICES, blank=True, null=True
    )
    surgery_name = models.CharField(max_length=100, blank=True)
    speciality = models.CharField(max_length=100)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name=_("Suburb/Town/City"))
    postcode = models.CharField(max_length=20, blank=True, null=True)
    state = models.ForeignKey(
        State,
        verbose_name=_("State/Province/Territory"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    fax = models.CharField(max_length=30, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["family_name"]

    def __str__(self):
        return "%s %s (%s)" % (
            self.family_name.upper(),
            self.given_names,
            self.surgery_name,
        )


class NextOfKinRelationship(models.Model):
    relationship = models.CharField(
        unique=True, max_length=100, verbose_name=_("Relationship")
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Next of Kin Relationship")

    def __str__(self):
        return gettext(self.relationship)


class PatientManager(models.Manager):
    def get_by_registry(self, *registries):
        return self.model.objects.filter(rdrf_registry__in=registries)

    def get_by_working_group(self, user):
        return self.model.objects.filter(
            working_groups__in=get_working_groups(user)
        )

    def get_by_registry_and_working_group(self, registry, user):
        return self.model.objects.filter(
            rdrf_registry=registry, working_groups__in=get_working_groups(user)
        )

    def get_filtered(self, user):
        return (
            self.model.objects.filter(
                rdrf_registry__id__in=get_registries(user)
            )
            .filter(working_groups__in=get_working_groups(user))
            .distinct()
        )

    def get_filtered_unallocated(self, user):
        return self.model.objects.filter(
            working_groups__in=get_working_groups(user)
        ).exclude(rdrf_registry__isnull=False)

    # what's returned when an ordinary query like Patient.objects.all() is used
    def get_queryset(self):
        # do NOT include inactive ( soft-deleted/archived) patients
        return super(PatientManager, self).get_queryset().filter(active=True)

    def really_all(self):
        # shows archived ( soft-deleted/archived ) patients also
        return super(PatientManager, self).get_queryset().all()

    def inactive(self):
        return self.really_all().filter(active=False)

    def get_by_clinician(self, clinician, registry_model):
        filters = []
        if registry_model.has_feature(
            RegistryFeatures.CLINICIANS_SEE_CREATED_PATIENTS
        ):
            filters.append(Q(created_by=clinician))
        if registry_model.has_feature(
            RegistryFeatures.CLINICIANS_HAVE_PATIENTS
        ):
            filters.append(Q(registered_clinicians__in=[clinician]))
        if (
            registry_model.has_feature(
                RegistryFeatures.CLINICIAN_ETHICAL_CLEARANCE
            )
            and clinician.ethically_cleared
        ):
            filters.append(Q(working_groups__in=clinician.working_groups.all()))

        if filters:
            query = reduce(lambda a, b: a | b, filters)
            return self.model.objects.filter(
                Q(rdrf_registry=registry_model) & query
            ).distinct()
        return self.none()

    def get_by_user_and_registry(self, user, registry_model):
        qs = self.get_queryset()
        if user.is_superuser:
            return qs.filter(rdrf_registry=registry_model)
        if user.is_curator:
            return qs.filter(
                rdrf_registry=registry_model,
                working_groups__in=user.working_groups.all(),
            ).distinct()
        if user.is_working_group_staff:
            return qs.filter(working_groups__in=user.working_groups.all())
        if user.is_clinician:
            return self.get_by_clinician(user, registry_model)
        if user.is_patient:
            return qs.filter(user=user)
        if user.is_carer:
            return qs.filter(carer=user)
        if user.is_parent:
            if parent_guardian := ParentGuardian.objects.filter(
                user=user
            ).first():
                return qs & parent_guardian.patient.all()
        return qs.none()


class LivingStates:
    ALIVE = "Alive"
    DECEASED = "Deceased"

    CHOICES = (
        (ALIVE, _("Living")),
        (DECEASED, _("Deceased")),
    )


class Patient(models.Model):
    SEX_CHOICES = (
        ("1", _("Male")),
        ("2", _("Female")),
        ("3", _("Indeterminate")),
    )

    ETHNIC_ORIGIN = (
        ("New Zealand European", _("New Zealand European")),
        ("Australian", _("Australian")),
        ("Other Caucasian/European", _("Other Caucasian/European")),
        ("Aboriginal", _("Aboriginal")),
        (
            "Person from the Torres Strait Islands",
            _("Person from the Torres Strait Islands"),
        ),
        ("Maori", _("Maori")),
        ("NZ European / Maori", _("NZ European / Maori")),
        ("Samoan", _("Samoan")),
        ("Cook Islands Maori", _("Cook Islands Maori")),
        ("Tongan", _("Tongan")),
        ("Niuean", _("Niuean")),
        ("Tokelauan", _("Tokelauan")),
        ("Fijian", _("Fijian")),
        ("Other Pacific Peoples", _("Other Pacific Peoples")),
        ("Southeast Asian", _("Southeast Asian")),
        ("Chinese", _("Chinese")),
        ("Indian", _("Indian")),
        ("Other Asian", _("Other Asian")),
        ("Middle Eastern", _("Middle Eastern")),
        ("Latin American", _("Latin American")),
        ("Black African/African American", _("Black African/African American")),
        ("Other Ethnicity", _("Other Ethnicity")),
        ("Decline to Answer", _("Decline to Answer")),
    )

    objects = PatientManager()
    rdrf_registry = models.ManyToManyField(
        Registry, related_name="patients", verbose_name=_("Registry")
    )
    working_groups = models.ManyToManyField(
        registry.groups.models.WorkingGroup,
        related_name="my_patients",
        verbose_name=_("Working Group"),
    )
    consent = models.BooleanField(
        null=False,
        blank=False,
        help_text=_(
            "The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them."
        ),
        verbose_name=_("consent given"),
    )
    consent_clinical_trials = models.BooleanField(
        null=False,
        blank=False,
        help_text=_(
            "Consent given to be contacted about clinical trials or other studies related to their condition."
        ),
        default=False,
    )
    consent_sent_information = models.BooleanField(
        null=False,
        blank=False,
        help_text=_("Consent given to be sent information on their condition"),
        verbose_name=_("consent to be sent information given"),
        default=False,
    )
    consent_provided_by_parent_guardian = models.BooleanField(
        null=False,
        blank=False,
        help_text=_(
            "Parent/Guardian consent provided on behalf of the patient."
        ),
        default=False,
    )
    family_name = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Family Name")
    )
    given_names = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Given Names")
    )
    maiden_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Maiden name (if applicable)"),
    )
    umrn = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Hospital/Clinic ID"),
    )
    date_of_birth = models.DateField(verbose_name=_("Date of birth"))
    date_of_death = models.DateField(
        verbose_name=_("Date of death"), null=True, blank=True
    )
    place_of_birth = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Place of birth")
    )

    date_of_migration = models.DateField(
        blank=True, null=True, verbose_name=_("Date of migration")
    )
    country_of_birth = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Country of birth"),
    )
    ethnic_origin = models.CharField(
        choices=ETHNIC_ORIGIN,
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Ethnic origin"),
    )
    sex = models.CharField(
        max_length=1, choices=SEX_CHOICES, verbose_name=_("Sex")
    )
    home_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Home phone")
    )
    mobile_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Mobile phone")
    )
    work_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Work phone")
    )
    email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    next_of_kin_family_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Family name")
    )
    next_of_kin_given_names = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Given names")
    )
    next_of_kin_relationship = models.ForeignKey(
        NextOfKinRelationship,
        verbose_name=_("Relationship"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    next_of_kin_address = models.TextField(
        blank=True, null=True, verbose_name=_("Address")
    )
    next_of_kin_suburb = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Suburb/Town")
    )
    next_of_kin_state = models.CharField(
        max_length=20,
        verbose_name=_("State/Province/Territory"),
        blank=True,
        null=True,
    )
    next_of_kin_postcode = models.IntegerField(
        verbose_name=_("Postcode"), blank=True, null=True
    )
    next_of_kin_home_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Home phone")
    )
    next_of_kin_mobile_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Mobile phone")
    )
    next_of_kin_work_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name=_("Work phone")
    )
    next_of_kin_email = models.EmailField(
        blank=True, null=True, verbose_name=_("Email")
    )
    next_of_kin_parent_place_of_birth = models.CharField(
        max_length=100,
        verbose_name=_("Place of birth of parents"),
        blank=True,
        null=True,
    )
    next_of_kin_country = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Country")
    )
    doctors = models.ManyToManyField(Doctor, through="PatientDoctor")
    active = models.BooleanField(
        default=True,
        help_text=_(
            "Ticked if active in the registry, ie not a deleted record, or deceased patient."
        ),
    )
    inactive_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Reason"),
        help_text=_("Please provide reason for deactivating the patient"),
    )
    registered_clinicians = models.ManyToManyField(
        CustomUser,
        related_name="registered_patients",
        blank=True,
        verbose_name=_("Registered clinicians"),
    )
    user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="user_object",
        on_delete=models.SET_NULL,
    )

    carer = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="patients_in_care",
        on_delete=models.SET_NULL,
    )

    living_status = models.CharField(
        choices=LivingStates.CHOICES,
        max_length=80,
        default=LivingStates.ALIVE,
        verbose_name=_("Living status"),
    )

    # The following is intended as a hidden field which is set only
    # via registration process for those registries which support registration
    # It allows
    patient_type = models.CharField(
        max_length=80, blank=True, null=True, verbose_name=_("Patient Type")
    )

    stage = models.ForeignKey(
        "patients.PatientStage",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    last_updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    last_updated_overall_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="created_patient_object",
        on_delete=models.SET_NULL,
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["family_name", "given_names", "date_of_birth"]
        verbose_name_plural = _("Patient List")

        permissions = (
            ("can_see_full_name", _("Can see Full Name column")),
            ("can_see_dob", _("Can see Date of Birth column")),
            ("can_see_working_groups", _("Can see Working Groups column")),
            (
                "can_see_diagnosis_progress",
                _("Can see Diagnosis Progress column"),
            ),
            (
                "can_see_diagnosis_currency",
                _("Can see Diagnosis Currency column"),
            ),
            ("can_see_data_modules", _("Can see Data Modules column")),
            ("can_see_code_field", _("Can see Code Field column")),
            ("can_see_living_status", _("Can see Living Status column")),
        )

    def as_dto(self):
        return PatientDTO(
            **{
                **{f: getattr(self, f) for f in patientdto_attr_fields},
                **{
                    "working_groups": list(
                        self.working_groups.values_list("name", flat=True)
                    )
                },
            }
        )

    @property
    def code_field(self):
        gender_options = {
            "1": _("Male"),
            "2": _("Female"),
            "3": _("Indeterminate"),
        }

        gender_string = gender_options[self.sex]

        if self.patient_type is not None:
            patient_type_string = _(self.patient_type.capitalize())

            return_str = str(
                "{0} {1}".format(gender_string, patient_type_string)
            )
            return return_str
        else:
            return_str = str("{0}".format(gender_string))
            return return_str

    @property
    def display_name(self):
        if self.active:
            return "%s %s" % (self.family_name, self.given_names)
        else:
            return "%s %s (Archived)" % (self.family_name, self.given_names)

    @property
    def patient_info(self):
        return {
            "dob": self.date_of_birth.strftime("%Y-%m-%d"),
            "gender": dict(self.SEX_CHOICES).get(self.sex),
            "ancestry": self.ethnic_origin,
            "age": self.age,
            "guid": self.guid,
        }

    @property
    def age(self):
        """in years"""

        def calculate_age(born):
            if self.date_of_death:
                compare_date = self.date_of_death
            else:
                compare_date = datetime.date.today()

            try:
                birthday = born.replace(year=compare_date.year)
            # raised when birthdate is February 29 and the current year is not a leap year
            except ValueError:
                birthday = born.replace(
                    year=compare_date.year, month=born.month + 1, day=1
                )

            if birthday > compare_date:
                return compare_date.year - born.year - 1
            else:
                return compare_date.year - born.year

        try:
            age_in_years = calculate_age(self.date_of_birth)
            return age_in_years
        except BaseException:
            return None

    @property
    def display_age(self):
        return f'{self.age} {_("years")}'

    @property
    def guid(self):
        supports_guid = any(
            r.has_feature(RegistryFeatures.PATIENT_GUID)
            for r in self.rdrf_registry.all()
        )
        if supports_guid and hasattr(self, "patientguid"):
            return self.patientguid.guid

    def has_feature(self, feature):
        return any([r.has_feature(feature) for r in self.rdrf_registry.all()])

    @property
    def is_linked(self):
        """
        Am I linked to other relative patients ( only applicable to patients in
        registries that allow creation of patient relatives
        """
        if not self.is_index:
            return False

        for patient_relative in self.relatives.all():
            if patient_relative.relative_patient:
                return True

        return False

    def get_archive_url(self, registry_model):
        patient_detail_link = reverse(
            "v1:patient-detail", args=(registry_model.code, self.pk)
        )
        return patient_detail_link

    @property
    def working_groups_display(self):
        return ",".join([wg.display_name for wg in self.working_groups.all()])

    @property
    def home_address(self):
        return self.patientaddress_set.filter(address_type__type="Home").first()

    def clinical_data_currency(self, days=365):
        """
        If some clinical form has been updated  in the window
        then the data for that registry is considered "current" - this mirrors
        """
        time_window_start = datetime.datetime.now() - datetime.timedelta(
            days=days
        )
        currency_map = {}
        for registry_model in self.rdrf_registry.all():
            last_updated_in_window = False
            for form_model in registry_model.forms:
                form_timestamp = self.get_form_timestamp(form_model)
                if form_timestamp and form_timestamp >= time_window_start:
                    last_updated_in_window = True
                    break
            currency_map[registry_model.code] = last_updated_in_window

        return currency_map

    def get_form_value(
        self,
        registry_code,
        form_name,
        section_code,
        data_element_code,
        multisection=False,
        context_id=None,
        clinical_data=None,
    ):
        # if clinical_data is supplied don't reload
        # ( allows faster retrieval of multiple values
        from rdrf.db.dynamic_data import DynamicDataWrapper
        from rdrf.helpers.utils import mongo_key

        if clinical_data is None:
            wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)
            data = wrapper.load_dynamic_data(registry_code, "cdes")
        else:
            data = clinical_data

        key = mongo_key(form_name, section_code, data_element_code)

        if data is None:
            # no clinical data
            raise KeyError(key)
        else:
            if multisection:
                sections = data[section_code]
                values = []
                for section in sections:
                    if key in section and section[key]:
                        values.append(section[key])
                return values
            else:
                return data[key]

    def update_field_expressions(
        self, registry_model, field_expressions, context_model=None
    ):
        from rdrf.db.dynamic_data import DynamicDataWrapper
        from rdrf.db.generalised_field_expressions import (
            GeneralisedFieldExpressionParser,
        )

        if (
            registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is None
        ):
            raise Exception("No context model set")
        elif (
            not registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is not None
        ):
            raise Exception(
                "context model should not be explicit for non-supporting registry"
            )
        elif (
            not registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is None
        ):
            # the usual case
            from rdrf.db.contexts_api import RDRFContextManager

            rdrf_context_manager = RDRFContextManager(registry_model)
            context_model = rdrf_context_manager.get_or_create_default_context(
                self
            )

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)
        parser = GeneralisedFieldExpressionParser(registry_model)
        mongo_data = wrapper.load_dynamic_data(
            registry_model.code, "cdes", flattened=False
        )

        errors = 0
        error_messages = []
        succeeded = 0
        total = 0

        for field_expression, new_value in field_expressions:
            total += 1
            try:
                expression_object = parser.parse(field_expression)
            except Exception:
                errors += 1
                error_messages.append("Parse error: %s" % field_expression)
                continue

            try:
                self, mongo_data = expression_object.set_value(
                    self, mongo_data, new_value, context_id=context_model.pk
                )
                succeeded += 1
            except NotImplementedError:
                errors += 1
                error_messages.append("Not Implemented: %s" % field_expression)
                continue

            except Exception as ex:
                errors += 1
                error_messages.append(
                    "Error setting value for %s: %s" % (field_expression, ex)
                )

        try:
            wrapper.update_dynamic_data(registry_model, mongo_data)
        except Exception as ex:
            logger.error("Error update_dynamic_data: %s" % ex)
            error_messages.append("Failed to u/pdate: %s" % ex)
        try:
            self.save()
        except Exception as ex:
            error_messages.append("Failed to save patient: %s" % ex)

        return error_messages

    def evaluate_field_expression(
        self, registry_model, field_expression, **kwargs
    ):
        if "value" in kwargs:
            setting_value = True
            value = kwargs["value"]
        else:
            setting_value = False

        # TODO need to support contexts - supply in kwargs
        if "context_model" not in kwargs:
            context_model = self.default_context(registry_model)
        else:
            context_model = kwargs["context_model"]

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)

        if "clinical_data" in kwargs:
            mongo_data = kwargs["clinical_data"]
        else:
            mongo_data = wrapper.load_dynamic_data(
                registry_model.code, "cdes", flattened=False
            )

        from rdrf.db.generalised_field_expressions import (
            GeneralisedFieldExpressionParser,
        )

        parser = GeneralisedFieldExpressionParser(registry_model)

        if mongo_data is None:
            # ensure we have sane data frame
            mongo_data = {
                "django_id": self.pk,
                "django_model": "Patient",
                "timestamp": datetime.datetime.now(),
                "context_id": context_model.pk,
                "forms": [],
            }

        if not setting_value:
            # ie retrieving a value
            # or doing an action like clearing a multisection
            action = parser.parse(field_expression)
            return action(self, mongo_data)
        else:
            setter = parser.parse(field_expression)
            # operate on patient_model supplying value
            # gfe's operate on either sql or mongo
            patient_model, mongo_data = setter.set_value(
                self, mongo_data, value
            )
            patient_model.save()
            return wrapper.update_dynamic_data(registry_model, mongo_data)

    def set_form_value(
        self,
        registry_code,
        form_name,
        section_code,
        data_element_code,
        value,
        context_model=None,
        save_snapshot=False,
        user=None,
    ):
        from rdrf.db.dynamic_data import DynamicDataWrapper
        from rdrf.forms.progress.form_progress import FormProgress
        from rdrf.helpers.utils import mongo_key
        from rdrf.models.definition.models import Registry, RegistryForm

        registry_model = Registry.objects.get(code=registry_code)
        if (
            registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is None
        ):
            raise Exception("No context model set")
        elif (
            not registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is not None
        ):
            raise Exception(
                "context model should not be explicit for non-supporting registry"
            )
        elif (
            not registry_model.has_feature(RegistryFeatures.CONTEXTS)
            and context_model is None
        ):
            # the usual case
            from rdrf.db.contexts_api import RDRFContextManager

            rdrf_context_manager = RDRFContextManager(registry_model)
            context_model = rdrf_context_manager.get_or_create_default_context(
                self
            )

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)
        if user:
            wrapper.user = user

        form_model = RegistryForm(name=form_name, registry=registry_model)
        wrapper.current_form_model = form_model

        mongo_data = wrapper.load_dynamic_data(registry_code, "cdes") or {}
        key = mongo_key(form_name, section_code, data_element_code)
        timestamp = "%s_timestamp" % form_name
        t = datetime.datetime.now()

        frm = RegistryForm.objects.get(
            registry__code=registry_code, name=form_name
        )
        mongo_data[key] = value
        mongo_data[timestamp] = t
        wrapper.save_dynamic_data(
            registry_model, "cdes", DataDefinitions(frm), mongo_data
        )

        handle_file_notifications(registry_model, self, wrapper.filestorage)

        # update form progress
        form_progress_calculator = FormProgress(registry_model)
        form_progress_calculator.save_for_patient(self, context_model)

        if save_snapshot and user is not None:
            wrapper.save_snapshot(
                registry_code,
                "cdes",
                form_name=form_model.name,
                form_user=user.username,
            )

    def in_registry(self, reg_code):
        """
        returns True if patient belongs to the registry with reg code provided
        """
        for registry_model in self.rdrf_registry.all():
            if registry_model.code == reg_code:
                return True

    @property
    def my_index(self):
        # This property is only applicable to FH
        if self.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            # try to find patient relative object corresponding to this patient and
            # then locate that relative's index patient
            try:
                patient_relative = PatientRelative.objects.get(
                    relative_patient=self
                )
                if patient_relative.patient:
                    return patient_relative.patient
                else:
                    return None
            except PatientRelative.DoesNotExist:
                return None

        return None

    def get_contexts_url(self, registry_model):
        # TODO - change so we don't need this
        return None
        if not registry_model.has_feature(RegistryFeatures.CONTEXTS):
            return None
        else:
            base_url = reverse("contextslisting")
            full_url = "%s?registry_code=%s&patient_id=%s" % (
                base_url,
                registry_model.code,
                self.pk,
            )
            return full_url

    def sync_patient_relative(self):
        # If there is a patient relative ( from which I was created)
        # then synchronise my common properties:
        try:
            pr = PatientRelative.objects.get(relative_patient=self)
        except PatientRelative.DoesNotExist:
            return

        pr.given_names = self.given_names
        pr.family_name = self.family_name
        pr.date_of_birth = self.date_of_birth
        pr.sex = self.sex
        pr.living_status = self.living_status

        # sever the link if we've deactivated
        if not self.active:
            pr.relative_patient = None

        pr.save()

    def update_clinicaldata_model(self):
        patient_id = self.id
        clinicaldata_models = ClinicalData.objects.filter(
            django_id=patient_id, django_model="Patient"
        )

        for cd in clinicaldata_models:
            if cd.active:
                cd.active = False
                cd.save()

    def hard_delete_clinicaldata(self, patient_id):
        clinicaldata_models = ClinicalData.objects.filter(
            django_id=patient_id, django_model="Patient"
        )
        for cd in clinicaldata_models:
            cd.delete()

    def notify_consent_changes(self, registry, changes):
        if len(changes) == 0:
            return

        def describe(change):
            if change.answer:
                return "checked"
            return (
                "left unchecked" if change.last_update is None else "unchecked"
            )

        formatted_changes = [
            {
                "question": c.consent_question.question_label,
                "answer": c.answer,
                "is_new": c.last_update is None,
                "description": describe(c),
            }
            for c in changes
        ]
        template_data = {
            "patient": self,
            "consent_changes": formatted_changes,
        }
        process_notification(
            registry.code,
            EventType.PATIENT_CONSENT_CHANGE,
            template_data,
        )

    def set_consent(self, consent_model, answer=True, commit=True):
        patient_registries = [r for r in self.rdrf_registry.all()]
        if consent_model.section.registry not in patient_registries:
            return  # error?
        cv, created = ConsentValue.objects.get_or_create(
            consent_question=consent_model, patient=self
        )
        answer_changed = cv.answer != answer or created
        cv.answer = answer
        if cv.first_save:
            cv.last_update = datetime.datetime.now()
        else:
            cv.first_save = datetime.datetime.now()
        if commit:
            cv.save()
        return cv, answer_changed

    def get_consent(self, consent_model, field="answer"):
        patient_registries = [r for r in self.rdrf_registry.all()]
        if consent_model.section.registry not in patient_registries:
            if field == "answer":
                return False  # ?
            else:
                return None
        try:
            cv = ConsentValue.objects.get(
                patient=self, consent_question=consent_model
            )
            if field == "answer":
                return cv.answer
            elif field == "first_save":
                return cv.first_save
            elif field == "last_update":
                return cv.last_update
            else:
                raise ValueError(
                    "only consent_value answer, first_save, last_update fields allowed"
                )

        except ConsentValue.DoesNotExist:
            if field == "answer":
                return False  # ?
            else:
                return None

    @property
    def consent_questions_data(self):
        d = {}
        for consent_value in ConsentValue.objects.filter(patient=self):
            consent_question_model = consent_value.consent_question
            d[consent_question_model.field_key] = consent_value.answer
        return d

    def clean_consents(self):
        my_registries = [r for r in self.rdrf_registry.all()]
        for consent_value in ConsentValue.objects.filter(patient=self):
            if (
                consent_value.consent_question.section.registry
                not in my_registries
            ):
                consent_value.delete()

    @property
    def is_index(self):
        if not self.active:
            return False

        if not self.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            return False
        else:
            if not self.my_index:
                return True
            else:
                return False

    def mark_changed_timestamp(self):
        # Does an update through the QuerySet on purpose, so if only the last updated timestamp field
        # changed (and none of the patient data) we don't execute any custom business logic
        # in save(), pre-, and post- save signals.
        Patient.objects.filter(pk=self.pk).update(
            last_updated_overall_at=timezone.now()
        )

    @property
    def has_guardian(self):
        return ParentGuardian.objects.filter(patient=self).count() > 0

    @property
    def combined_name(self):
        if self.has_guardian:
            guardians = [
                pg for pg in ParentGuardian.objects.filter(patient=self)
            ]
            g = guardians[0]
            name = "%s on behalf of %s" % (g, self)
            return name
        else:
            return "%s" % self

    def __str__(self):
        if self.active:
            return "%s %s" % (self.family_name, self.given_names)
        else:
            return "%s %s (Archived)" % (self.family_name, self.given_names)

    def save(self, *args, **kwargs):
        if hasattr(self, "family_name"):
            self.family_name = stripspaces(self.family_name).upper()

        if hasattr(self, "given_names"):
            self.given_names = stripspaces(self.given_names)

        if not self.pk:
            self.active = True

        self.last_updated_overall_at = timezone.now()

        super(Patient, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        If a user deletes a patient it's active flag will be true, so we should set it to false.
        If a superuser deletes a patent it's active flag is false, so we should delete the object.
        """
        if self.active:
            self.active = False
            self.save()
            self.sync_patient_relative()
            self.update_clinicaldata_model()

    def _hard_delete(self, *args, **kwargs):
        # real delete!
        patient_id = self.id
        super(Patient, self).delete(*args, **kwargs)
        self.hard_delete_clinicaldata(patient_id)

    def get_reg_list(self):
        return ", ".join([r.name for r in self.rdrf_registry.all()])

    get_reg_list.short_description = "Registry"

    def form_progress(self, registry_form, numbers_only=False):
        if not registry_form.has_progress_indicator:
            if numbers_only:
                return 0, 0

            return [], 0

        required = 0
        set_count = 0
        cdes_status = {}
        registry_model = registry_form.registry
        registry_code = registry_model.code
        cde_codes_required = [
            cde.code for cde in registry_form.complete_form_cdes.all()
        ]
        for section_model in registry_form.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code in cde_codes_required:
                    required += 1
                    try:
                        cde_value = self.get_form_value(
                            registry_code,
                            registry_form.name,
                            section_model.code,
                            cde_model.code,
                            section_model.allow_multiple,
                        )
                    except KeyError:
                        cde_value = None

                    cdes_status[cde_model.name] = False
                    if cde_value:
                        cdes_status[cde_model.name] = True
                        set_count += 1

        if numbers_only:
            return set_count, required

        try:
            percentage = float(set_count) / float(required) * 100
        except ZeroDivisionError:
            percentage = 0

        return cdes_status, percentage

    def forms_progress(self, registry_model, forms):
        from rdrf.helpers.utils import mongo_key

        mongo_data = DynamicDataWrapper(self).load_dynamic_data(
            registry_model.code, "cdes"
        )
        total_filled_in = 0
        total_required_for_completion = 0

        for registry_form in forms:
            if not registry_form.has_progress_indicator:
                continue

            section_array = registry_form.sections.split(",")

            cde_complete = list(registry_form.complete_form_cdes.values())
            total_required_for_completion += len(
                registry_form.complete_form_cdes.values_list()
            )

            for cde in cde_complete:
                cde_section = ""
                for s in section_array:
                    section = Section.objects.get(code=s)
                    if cde["code"] in section.elements.split(","):
                        cde_section = s
                try:
                    cde_key = mongo_key(
                        registry_form.name, cde_section, cde["code"]
                    )
                    cde_value = mongo_data[cde_key]
                except KeyError:
                    cde_value = None

                if cde_value:
                    total_filled_in += 1

        return total_filled_in, total_required_for_completion

    def get_form_timestamp(self, registry_form, context_model=None):
        from django.core.exceptions import FieldError

        if context_model is not None:
            dynamic_store = DynamicDataWrapper(
                self, rdrf_context_id=context_model.pk
            )
        else:
            dynamic_store = DynamicDataWrapper(self)

        try:
            timestamp = dynamic_store.get_form_timestamp(registry_form)
        except FieldError:
            timestamp = None

        if timestamp:
            if "timestamp" in timestamp:
                ts = timestamp["timestamp"]
                return ts
            else:
                return timestamp

    def form_currency(self, registry_form):
        dynamic_store = DynamicDataWrapper(self)
        timestamp = dynamic_store.get_form_timestamp(registry_form)
        if timestamp:
            if "timestamp" in timestamp:
                ts = timestamp["timestamp"]
                delta = datetime.datetime.now() - ts
                return True if delta.days < _6MONTHS_IN_DAYS else False
            else:
                return True
        else:
            return False

    def as_json(self):
        return dict(
            obj_id=self.id,
            given_names=self.given_names,
            family_name=self.family_name,
            working_group=self.working_group.name,
            date_of_birth=str(self.date_of_birth),
        )

    @property
    def context_models(self):
        from django.contrib.contenttypes.models import ContentType

        from rdrf.models.definition.models import RDRFContext

        contexts = []
        content_type = ContentType.objects.get_for_model(self)

        for context_model in (
            RDRFContext.objects.select_related("context_form_group")
            .filter(content_type=content_type, object_id=self.pk)
            .order_by("created_at")
        ):
            contexts.append(context_model)
        return contexts

    def get_multiple_contexts(self, multiple_form_group):
        # Return all context models in 1 multiple context form group
        # We need this ordering of the group's context accessible from the patient
        # listing and the launcher
        registry_model = multiple_form_group.registry
        from rdrf.helpers.utils import MinType

        # if values are missing in the record we want to sort on
        # we get KeyErrors
        # can't use None to sort so we have to use this tricky thing
        bottom = MinType()

        def keyfunc(context_model):
            name_path = multiple_form_group.naming_cde_to_use
            if name_path:
                form_name, section_code, cde_code = name_path.split("/")
                section_model = Section.objects.get(code=section_code)
                is_multisection = section_model.allow_multiple

                try:
                    value = self.get_form_value(
                        registry_model.code,
                        form_name,
                        section_code,
                        cde_code,
                        multisection=is_multisection,
                        context_id=context_model.id,
                    )

                    if value is None:
                        return bottom
                    else:
                        return value
                except KeyError:
                    return bottom
            else:
                return multiple_form_group.get_default_name

        if multiple_form_group.ordering == "N":
            key_func = keyfunc
        else:

            def key_func(c):
                return c.created_at

        contexts = [
            c
            for c in self.context_models
            if c.context_form_group is not None
            and c.context_form_group.pk == multiple_form_group.pk
        ]

        return sorted(contexts, key=key_func, reverse=True)

    def get_forms_by_group(self, context_form_group, user=None):
        """
        Return links (pair of url and text)
        to existing forms "of type" (ie being in a context with a link to)  context_form_group

        """
        assert (
            context_form_group.supports_direct_linking
        ), "Context Form group must only contain one form"
        form_model = context_form_group.forms[0]
        if user and not user.can_view(form_model):
            return []

        def matches_context_form_group(cm):
            return (
                cm.context_form_group
                and cm.context_form_group.pk == context_form_group.pk
            )

        context_models = sorted(
            [
                cm
                for cm in self.context_models
                if matches_context_form_group(cm)
            ],
            key=lambda cm: cm.context_form_group.get_ordering_value(self, cm),
            reverse=True,
        )

        def link_text(cm):
            return cm.context_form_group.get_name_from_cde(self, cm)

        def link_url(cm):
            return reverse(
                "registry_form",
                args=(cm.registry.code, form_model.id, self.pk, cm.id),
            )

        return [(cm.id, link_url(cm), link_text(cm)) for cm in context_models]

    def default_context(self, registry_model):
        # return None if doesn't make sense
        from rdrf.models.definition.models import RegistryType

        registry_type = registry_model.registry_type
        if registry_type == RegistryType.NORMAL:
            my_contexts = self.context_models
            num_contexts = len(my_contexts)
            if num_contexts == 1:
                return my_contexts[0]
            else:
                raise Exception(
                    "default context could not be returned: num contexts = %s"
                    % num_contexts
                )

        elif registry_type == RegistryType.HAS_CONTEXTS:
            return None
        else:
            # registry has context form groups defined
            for context_model in self.context_models:
                if context_model.context_form_group:
                    if context_model.context_form_group.is_default:
                        return context_model
            raise Exception("no default context")

    def get_dynamic_data(
        self, registry_model, collection="cdes", context_id=None
    ):
        from rdrf.db.dynamic_data import DynamicDataWrapper

        if context_id is None:
            default_context = self.default_context(registry_model)
            if default_context is not None:
                context_id = default_context.pk
            else:
                raise Exception(
                    "need context id to get dynamic data for patient %s"
                    % self.pk
                )

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)

        return wrapper.load_dynamic_data(
            registry_model.code, collection, flattened=False
        )

    def update_dynamic_data(
        self, registry_model, new_mongo_data, context_id=None
    ):
        """
        Completely replace a patient's mongo record
        Dangerous - assumes new_mongo_data is correct structure
        Trying it to simulate rollback if update fails
        """
        from rdrf.db.dynamic_data import DynamicDataWrapper

        if context_id is None:
            default_context = self.default_context(registry_model)
            if default_context is not None:
                context_id = default_context.pk
            else:
                raise Exception(
                    "need context id to get update dynamic data for patient %s"
                    % self.pk
                )

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)
        # NB warning this completely replaces the existing mongo record for the patient
        # useful for "rolling back" after update failure
        logger.info(
            "Warning! : Updating existing dynamic data for %s(%s) in registry %s"
            % (self, self.pk, registry_model)
        )
        logger.info("New Mongo data record = %s" % new_mongo_data)
        if new_mongo_data is not None:
            wrapper.update_dynamic_data(registry_model, new_mongo_data)

    @property
    def family(self):
        return Family(self)


class PatientUpdateMixin:
    def update_patient_overall_ts(self):
        if self.patient:
            self.patient.last_updated_overall_at = timezone.now()
            self.patient.save()

    def save(self, *args, **kwargs):
        self.update_patient_overall_ts()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.update_patient_overall_ts()
        return super().delete(*args, **kwargs)


class PatientStage(models.Model):
    registry = models.ForeignKey(
        Registry, on_delete=models.CASCADE, related_name="+"
    )
    name = models.CharField(max_length=200)
    allowed_prev_stages = models.ManyToManyField(
        "self", symmetrical=False, related_name="+", blank=True
    )
    allowed_next_stages = models.ManyToManyField(
        "self", symmetrical=False, related_name="+", blank=True
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return self.name


class PatientStageRule(models.Model):
    FLOW_RULES = (
        (PatientState.REGISTERED, "Patient registered"),
        (PatientState.CONSENTED, "Patient provided consent"),
    )
    registry = models.ForeignKey(
        Registry, on_delete=models.CASCADE, related_name="+"
    )
    from_stage = models.ForeignKey(
        PatientStage,
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )
    condition = models.CharField(
        choices=FLOW_RULES, blank=False, null=True, max_length=32
    )
    to_stage = models.ForeignKey(
        PatientStage,
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = (("registry", "from_stage", "condition", "to_stage"),)

    def __str__(self):
        return f"PatientStageRule: {self.from_stage} {self.condition} {self.to_stage}"


class Speciality(models.Model):
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class ClinicianOther(models.Model, PatientUpdateMixin):
    use_other = models.BooleanField(default=False)
    patient = models.ForeignKey(Patient, null=True, on_delete=models.SET_NULL)
    clinician_name = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Clinician Name")
    )
    clinician_hospital = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Clinician hospital"),
    )
    clinician_address = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Clinician address"),
    )
    clinician_email = models.EmailField(
        max_length=254, null=True, blank=True, verbose_name=_("Clinician email")
    )
    clinician_phone_number = models.CharField(
        max_length=254,
        null=True,
        blank=True,
        verbose_name=_("Clinician phone number"),
    )
    speciality = models.ForeignKey(
        Speciality,
        null=True,
        blank=True,
        on_delete=models.deletion.SET_NULL,
        verbose_name=_("Clinician specialty"),
    )
    user = models.ForeignKey(
        CustomUser, blank=True, null=True, on_delete=models.SET_NULL
    )
    clinician_first_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Clinician first name"),
    )
    clinician_last_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Clinician last name"),
    )

    history = HistoricalRecords()

    def synchronise_working_group(self):
        if not self.user:
            return

        if not self.use_other:
            if self.patient:
                wgs = [wg for wg in self.user.working_groups.all()]
                self.patient.working_groups.set(wgs)
                self.patient.save()
                # fkrp use case
                # if the patient is a user update the user working groups to match
                if self.patient.user:
                    self.patient.user.working_groups.set(
                        [wg for wg in self.patient.working_groups.all()]
                    )
                    self.patient.user.save()
                # if there user/parent of this patient then need to update their working
                # groups also
                try:
                    parent = ParentGuardian.objects.get(patient=self.patient)
                    if parent.user:
                        for wg in self.patient.working_groups.all():
                            parent.user.working_groups.add(wg)
                            parent.user.save()
                except ParentGuardian.DoesNotExist:
                    pass


@receiver(post_save, sender=ClinicianOther)
def other_clinician_post_save(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if not instance.user and instance.use_other and instance.clinician_email:
        # User has NOT selected an existing clinician
        other_clinician = instance
        patient = other_clinician.patient
        registry_model = patient.rdrf_registry.first()
        # model allows for patient to have more than one parent ...
        try:
            parent = ParentGuardian.objects.filter(patient=patient).first()
        except BaseException:
            # if patient was created not as child of a user
            parent = None

        template_data = {
            "patient": patient,
            "parent": parent,
            "other_clinician": instance,
        }
        # this sends an email notification to (a) curator
        process_notification(
            registry_model.code, EventType.OTHER_CLINICIAN, template_data
        )

        # new <?> workflow - we notify the clinician asking them to sign up and verify
        # this stores email from the model at the time of the request

        csr = ClinicianSignupRequest.create(
            registry_model=registry_model,
            patient_model=patient,
            clinician_email=other_clinician.clinician_email,
            clinician_other=other_clinician,
        )

        csr.send_request()


@receiver(post_save, sender=Patient)
def selected_clinician_notification(sender, instance, **kwargs):
    from rdrf.events.events import EventType
    from rdrf.services.io.notifications.email_notification import (
        process_notification,
    )

    if instance.registered_clinicians.exists() and hasattr(
        instance, "clinician_flag"
    ):
        registry_model = instance.rdrf_registry.first()
        template_data = {"patient": instance}
        process_notification(
            registry_model.code, EventType.CLINICIAN_SELECTED, template_data
        )

        # this is to prevent the working groups synching triggering the same notification
        # we only allow one per clinician selection event
        delattr(instance, "clinician_flag")


class ParentGuardian(models.Model):
    GENDER_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Place of birth"
    )
    date_of_migration = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
    state = models.CharField(
        max_length=20, verbose_name="State/Province/Territory"
    )
    postcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    patient = models.ManyToManyField(Patient)
    self_patient = models.ForeignKey(
        Patient,
        blank=True,
        null=True,
        related_name="self_patient",
        on_delete=models.SET_NULL,
    )
    user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="parent_user_object",
        on_delete=models.SET_NULL,
    )

    history = HistoricalRecords()

    @property
    def children(self):
        if not self.self_patient:
            return [p for p in self.patient.all()]
        else:
            return [
                p for p in self.patient.all() if p.pk != self.self_patient.pk
            ]

    def is_parent_of(self, other_patient):
        return other_patient in self.children

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for patient in self.patient.all():
            patient.last_updated_overall_at = timezone.now()
            patient.save()


@receiver(post_save, sender=ParentGuardian)
def update_my_user(sender, **kwargs):
    """
    Propagate name change on parent to user if they
    have one.
    """
    parent_guardian = kwargs["instance"]
    user = parent_guardian.user
    if user:
        user.first_name = parent_guardian.first_name
        user.last_name = parent_guardian.last_name
        user.save()


class AddressTypeManager(models.Manager):
    def get_by_natural_key(self, type):
        return self.get(type=type)


class AddressType(models.Model):
    objects = AddressTypeManager()

    type = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    history = HistoricalRecords()

    def natural_key(self):
        return (self.type,)

    def __str__(self):
        return "%s" % _(self.type)


class PatientAddress(models.Model, PatientUpdateMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    address_type = models.ForeignKey(
        AddressType,
        default=1,
        verbose_name=_("Address type"),
        on_delete=models.CASCADE,
    )
    address = models.TextField()
    suburb = models.CharField(max_length=100, verbose_name=_("Suburb/Town"))
    country = models.CharField(max_length=100, verbose_name=_("Country"))
    state = models.CharField(max_length=50, verbose_name=_("State"))
    postcode = models.CharField(max_length=50, verbose_name=_("Postcode"))

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = _("Patient Addresses")

    def __str__(self):
        return ""


class PatientConsentStorage(DefaultStorage):
    """
    This is a normal default file storage, except the URL points to
    authenticated file download view.
    """

    def url(self, name):
        consent = PatientConsent.objects.filter(form=name).first()
        if consent is not None:
            rev = dict(
                consent_id=consent.id, filename=consent.original_filename
            )
            return reverse("registry:consent-form-download", kwargs=rev)
        return None


def upload_patient_consent_to(instance, filename):
    return "patient/{0}/consents/{1}".format(
        instance.patient.pk, instance.filename
    )


class ConsentFileField(models.FileField):
    """
    Custom FileField that removes the storage from deconstruct.
    Without this each time you change the Default Storage class in settings, Django
    considers it a model change and wants you to create a migration.
    """

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "storage" in kwargs:
            del kwargs["storage"]
        return name, path, args, kwargs


class PatientConsent(models.Model, PatientUpdateMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    form = ConsentFileField(
        upload_to=upload_patient_consent_to,
        storage=PatientConsentStorage(),
        verbose_name="Consent form",
        blank=True,
        null=True,
    )
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)

    history = HistoricalRecords()


@receiver(pre_delete, sender=PatientConsent)
def consentfile_delete(sender, instance, **kwargs):
    logger.debug(f"Deleting file {instance.filename}")
    instance.form.delete(False)


class PatientSignature(models.Model, PatientUpdateMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    signature = models.TextField()


class PatientDoctor(models.Model, PatientUpdateMixin):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    relationship = models.CharField(max_length=50)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "medical professionals for patient"
        verbose_name_plural = "medical professionals for patient"


def get_countries():
    return [
        (c.alpha_2, c.name)
        for c in sorted(pycountry.countries, key=attrgetter("name"))
    ]


class PatientRelative(models.Model, PatientUpdateMixin):
    RELATIVE_TYPES = (
        ("Parent (1st degree)", "Parent (1st degree)"),
        ("Child (1st degree)", "Child (1st degree)"),
        ("Sibling (1st degree)", "Sibling (1st degree)"),
        ("Identical Twin (0th degree)", "Identical Twin (0th degree)"),
        ("Non-identical Twin (1st degree)", "Non-identical Twin (1st degree)"),
        ("Half Sibling (1st degree)", "Half Sibling (1st degree)"),
        ("Grandparent (2nd degree)", "Grandparent (2nd degree)"),
        ("Grandchild (2nd degree)", "Grandchild (2nd degree)"),
        ("Uncle/Aunt (2nd degree)", "Uncle/Aunt (2nd degree)"),
        ("Niece/Nephew (2nd degree)", "Niece/Nephew (2nd degree)"),
        ("1st Cousin (3rd degree)", "1st Cousin (3rd degree)"),
        ("Great Grandparent (3rd degree)", "Great Grandparent (3rd degree)"),
        ("Great Grandchild (3rd degree)", "Great Grandchild (3rd degree)"),
        ("Great Uncle/Aunt (3rd degree)", "Great Uncle/Aunt (3rd degree)"),
        ("Grand Niece/Nephew (3rd degree)", "Grand Niece/Nephew (3rd degree)"),
        (
            "1st Cousin once removed (4th degree)",
            "1st Cousin once removed (4th degree)",
        ),
        ("Spouse", "Spouse"),
        ("Unknown", "Unknown"),
        ("Other", "Other"),
    )

    RELATIVE_LOCATIONS = [
        ("AU - WA", "Australia - WA"),
        ("AU - SA", "Australia - SA"),
        ("AU - NSW", "Australia - NSW"),
        ("AU - QLD", "Australia - QLD"),
        ("AU - NT", "Australia - NT"),
        ("AU - VIC", "Australia - VIC"),
        ("AU - TAS", "Australia - TAS"),
        ("NZ", "New Zealand"),
    ]

    SEX_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))
    patient = models.ForeignKey(
        Patient, related_name="relatives", on_delete=models.CASCADE
    )
    family_name = models.CharField(max_length=100)
    given_names = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    relationship = models.CharField(choices=RELATIVE_TYPES, max_length=80)
    location = models.CharField(
        choices=RELATIVE_LOCATIONS + get_countries(), max_length=80
    )
    living_status = models.CharField(
        choices=LivingStates.CHOICES, max_length=80
    )
    relative_patient = models.OneToOneField(
        to=Patient,
        null=True,
        blank=True,
        related_name="as_a_relative",
        verbose_name="Create Patient?",
        on_delete=models.CASCADE,
    )

    history = HistoricalRecords()

    def create_patient_from_myself(self, registry_model, working_groups):
        # Create the patient corresponding to this relative
        p = Patient()
        p.given_names = self.given_names
        p.family_name = self.family_name
        p.date_of_birth = self.date_of_birth
        p.sex = self.sex
        p.consent = True  # tricky ?
        p.active = True
        p.living_status = self.living_status

        try:
            p.save()
        except Exception as ex:
            raise ValidationError(
                "Could not create patient from relative: %s" % ex
            )

        p.rdrf_registry.set([registry_model])
        p.working_groups.set(working_groups)
        p.save()
        self.relative_patient = p
        self.save()
        # explicitly set relative cde
        if registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            from rdrf.views.family_linkage import FamilyLinkageManager

            flm = FamilyLinkageManager(registry_model)
            flm.set_as_relative(p)
        return p

    def sync_relative_patient(self):
        if self.relative_patient:
            self.relative_patient.given_names = self.given_names
            self.relative_patient.family_name = self.family_name
            self.relative_patient.date_of_birth = self.date_of_birth
            self.relative_patient.sex = self.sex
            self.relative_patient.living_status = self.living_status
            self.relative_patient.save()


@receiver(post_delete, sender=PatientRelative)
def delete_created_patient(sender, instance, **kwargs):
    if instance.relative_patient:
        #  when doing family linkage operation of moving
        #  a relative to an index , we were seeing this
        #  signal archive the newly "promoted" relative's patient
        #  so don't do this!
        if not instance.relative_patient.is_index:
            if not hasattr(instance, "skip_archiving"):
                instance.relative_patient.delete()


@receiver(post_save, sender=Patient)
def clean_consents(sender, instance, **kwargs):
    instance.clean_consents()


@receiver(post_save, sender=Patient)
def sync_user(sender, instance, **kwargs):
    # ensure that changes to a patient name propagate
    # to any related user objects
    if instance.user:
        username = instance.user.username
        user = CustomUser.objects.get(username=username)
        user.first_name = instance.given_names
        user.last_name = instance.family_name
        user.save()


@receiver(post_save, sender=Patient)
def update_family_linkage_fields(sender, instance, **kwargs):
    logger.debug("updating family linkage fields")
    for registry_model in instance.rdrf_registry.all():
        logger.debug("checking %s" % registry_model)
        if registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            logger.debug("%s has family linkage" % registry_model)
            from rdrf.views.family_linkage import FamilyLinkageManager

            flm = FamilyLinkageManager(registry_model, None)
            if instance.is_index:
                logger.debug("%s is an index" % instance)
                flm.set_as_index_patient(instance)
            else:
                logger.debug("%s is a relative" % instance)
                flm.set_as_relative(instance)


@receiver(post_save, sender=Patient)
def update_living_status(sender, instance, created, raw, **kwargs):
    patient = instance
    if patient.date_of_death:
        if patient.living_status != LivingStates.DECEASED:
            patient.living_status = LivingStates.DECEASED
            patient.save()


@receiver(post_save, sender=Patient)
def generate_patient_guid(sender, instance, created, raw, **kwargs):
    existing = PatientGUID.objects.filter(patient=instance).exists()
    can_set_guid = any(
        r.has_feature(RegistryFeatures.PATIENT_GUID)
        for r in instance.rdrf_registry.all()
    )
    if can_set_guid and not existing:
        PatientGUID.objects.create(patient=instance)


def _get_registry_for_mongo(regs):
    registry_obj = Registry.objects.filter(pk__in=regs)
    json_str = serializers.serialize("json", registry_obj)
    json_obj = json.loads(json_str)

    json_final = []

    for reg in json_obj:
        reg["fields"]["id"] = reg["pk"]
        del reg["fields"]["splash_screen"]
        json_final.append(reg["fields"])

    return json_final


@receiver(m2m_changed, sender=Patient.rdrf_registry.through)
def registry_changed_on_patient(sender, **kwargs):
    if kwargs["action"] == "post_add":
        from rdrf.db.contexts_api import create_rdrf_default_contexts

        instance = kwargs["instance"]
        registry_ids = kwargs["pk_set"]
        create_rdrf_default_contexts(instance, registry_ids)


class ConsentValue(models.Model, PatientUpdateMixin):
    patient = models.ForeignKey(
        Patient, related_name="consents", on_delete=models.CASCADE
    )
    consent_question = models.ForeignKey(
        ConsentQuestion, on_delete=models.CASCADE
    )
    answer = models.BooleanField(default=False)
    first_save = models.DateField(null=True, blank=True)
    last_update = models.DateField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ("patient", "consent_question")

    def __str__(self):
        return "Consent Value for %s question %s is %s" % (
            self.patient,
            self.consent_question,
            self.answer,
        )


@receiver(post_delete, sender=PatientRelative)
def delete_associated_patient_if_any(sender, instance, **kwargs):
    if instance.relative_patient:
        if not hasattr(instance, "skip_archiving"):
            instance.relative_patient.delete()


class PatientGUIDManager(models.Manager):
    @staticmethod
    def _generate_guid():
        def randomString(letters, length):
            return "".join(random.choice(letters) for i in range(length))

        return randomString("ABCDEFGHJKLMNPRSTUVXYZ", 6) + randomString(
            "123456789", 4
        )

    def create(self, *args, **kwargs):
        if not kwargs.get("guid"):
            kwargs["guid"] = self._generate_unique_guid()
        return super().create(*args, **kwargs)

    def _generate_unique_guid(self):
        retries = 10
        for guid in (self._generate_guid() for __ in range(retries)):
            if not self.get_queryset().filter(guid=guid).exists():
                return guid
        raise Exception("Couldn't generate unique GUID for Patient")


class PatientGUID(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    guid = models.CharField(max_length=16, unique=True)

    objects = PatientGUIDManager()


patientdto_attr_fields = (
    "id",
    "consent",
    "consent_clinical_trials",
    "consent_sent_information",
    "consent_provided_by_parent_guardian",
    "family_name",
    "given_names",
    "maiden_name",
    "display_name",
    "umrn",
    "date_of_birth",
    "age",
    "date_of_death",
    "place_of_birth",
    "date_of_migration",
    "country_of_birth",
    "ethnic_origin",
    "sex",
    "home_phone",
    "mobile_phone",
    "work_phone",
    "email",
    "next_of_kin_family_name",
    "next_of_kin_given_names",
    "next_of_kin_relationship_id",
    "next_of_kin_address",
    "next_of_kin_suburb",
    "next_of_kin_state",
    "next_of_kin_postcode",
    "next_of_kin_home_phone",
    "next_of_kin_mobile_phone",
    "next_of_kin_work_phone",
    "next_of_kin_email",
    "next_of_kin_parent_place_of_birth",
    "next_of_kin_country",
    "living_status",
    "patient_type",
    "is_linked",
    "is_index",
    "my_index",
    "has_guardian",
)

PatientDTO = namedtuple(
    "PatientDTO", patientdto_attr_fields + ("working_groups",)
)


class LongitudinalFollowupQueueState(models.TextChoices):
    PENDING = "P"
    SENT = "S"


class LongitudinalFollowupEntry(models.Model):
    class Meta:
        ordering = ("send_at",)
        verbose_name_plural = "Longitudinal Followup Entries"
        indexes = (
            models.Index(
                name="idx_pending",
                fields=("state",),
                condition=Q(state=LongitudinalFollowupQueueState.PENDING),
            ),
        )

    longitudinal_followup = models.ForeignKey(
        LongitudinalFollowup, on_delete=models.CASCADE
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser, max_length=1, null=True, on_delete=models.SET_NULL
    )
    send_at = models.DateTimeField()
    sent_at = ArrayField(models.DateTimeField(), default=list)
    state = models.CharField(
        choices=LongitudinalFollowupQueueState.choices, max_length=1
    )
