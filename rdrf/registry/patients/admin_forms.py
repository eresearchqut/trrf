import base64
import binascii
import json
import logging
import uuid
from itertools import chain

from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from rdrf.db.dynamic_data import DynamicDataWrapper
from rdrf.forms.dynamic.fields import FileTypeRestrictedFileField
from rdrf.forms.widgets.widgets import (
    ConsentFileInput,
    CountryWidget,
    SignatureWidget,
    StateWidget,
)
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import (
    ConsentQuestion,
    ConsentSection,
    DemographicFields,
)
from registry.groups import GROUPS
from registry.groups.forms import working_group_fields
from registry.groups.models import CustomUser, WorkingGroup
from registry.patients.patient_widgets import PatientRelativeLinkWidget

from .models import (
    ParentGuardian,
    Patient,
    PatientAddress,
    PatientConsent,
    PatientDoctor,
    PatientRelative,
    PatientSignature,
    PatientStage,
    PatientStageRule,
    Registry,
)

logger = logging.getLogger(__name__)


class PatientDoctorForm(forms.ModelForm):
    OPTIONS = (
        (None, "---"),
        (1, _("GP (Primary Care)")),
        (2, _("Specialist (Lipid)")),
        (3, _("Primary Care")),
        (4, _("Paediatric Neurologist")),
        (5, _("Neurologist")),
        (6, _("Geneticist")),
        (7, _("Specialist - Other")),
        (8, _("Cardiologist")),
        (9, _("Nurse Practitioner")),
        (10, _("Paediatrician")),
    )

    # Sorting of options
    OPTIONS = tuple(sorted(OPTIONS, key=lambda item: item[1]))

    relationship = forms.ChoiceField(
        label=_("Type of Medical Professional"), choices=OPTIONS
    )

    class Meta:
        fields = "__all__"
        model = PatientDoctor


class PatientRelativeForm(forms.ModelForm):
    class Meta:
        model = PatientRelative
        fields = "__all__"  # Added after upgrading to Django 1.8
        # Added after upgrading to Django 1.8  - uniqueness check was failing
        # otherwise (RDR-1039)
        exclude = ["id"]
        widgets = {
            "relative_patient": PatientRelativeLinkWidget,
        }

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "datepicker"}, format="%d-%m-%Y"
        ),
        help_text=_("DD-MM-YYYY"),
        input_formats=["%d-%m-%Y"],
    )

    def __init__(self, *args, **kwargs):
        self.create_patient_data = None
        super(PatientRelativeForm, self).__init__(*args, **kwargs)
        self.create_patient_flag = False
        self.tag = None  # used to locate this form

    def _clean_fields(self):
        self._errors = ErrorDict()
        num_errors = 0
        if not self.is_bound:  # Stop further processing.
            return
        self.cleaned_data = {}
        # check for 'on' checkbox value for patient relative checkbox ( which means create patient )\
        # this 'on' value from widget is replaced by the pk of the created patient
        for name, field in list(self.fields.items()):
            try:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name)
                )
                if name == "relative_patient":
                    if value == "on":
                        self.cleaned_data[name] = None
                        self.create_patient_flag = True
                    else:
                        self.cleaned_data[name] = value

                elif name == "date_of_birth":
                    try:
                        self.cleaned_data[name] = self._set_date_of_birth(value)
                    except Exception:
                        raise ValidationError(
                            "Date of Birth must be dd-mm-yyyy"
                        )

                elif name == "patient":
                    continue  # this was causing error in post clean - we set this ourselves
                else:
                    self.cleaned_data[name] = value

            except ValidationError as e:
                num_errors += 1
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

        self.tag = (
            self.cleaned_data["given_names"] + self.cleaned_data["family_name"]
        )

    def _set_date_of_birth(self, dob):
        # todo figure  out why the correct input format is not being respected -
        # the field for dob on PatientRelative is in aus format already
        parts = dob.split("-")
        return "-".join([parts[2], parts[1], parts[0]])

    def _get_patient_relative_data(self, index):
        data = {}
        for k in self.data:
            if k.startswith("relatives-%s-" % index):
                data[k] = self.data[k]
        return data


class PatientAddressForm(forms.ModelForm):
    class Meta:
        model = PatientAddress
        fields = (
            "address_type",
            "address",
            "country",
            "state",
            "suburb",
            "postcode",
        )

    country = forms.ChoiceField(
        required=True,
        widget=CountryWidget(attrs={"onChange": "select_country(this);"}),
    )
    state = forms.ChoiceField(required=True, widget=StateWidget())
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))


class PatientConsentFileForm(forms.ModelForm):
    class Meta:
        model = PatientConsent
        fields = ["form"]
        exclude = ["filename", "original_filename"]

    form = FileTypeRestrictedFileField(widget=ConsentFileInput, required=False)

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = cleaned_data["form"]
        if not uploaded_file and self.instance.form:
            self.instance.form.delete(False)

    def save(self, commit=True):
        # remember the filename of the uploaded file
        logger.debug("File Saved")
        if self.cleaned_data.get("form"):
            self.instance.filename = uuid.uuid4()
            self.instance.original_filename = self.cleaned_data["form"].name
        return super(PatientConsentFileForm, self).save(commit)


class PatientSignatureForm(forms.ModelForm):
    class Meta:
        model = PatientSignature
        fields = ["signature"]

    signature = forms.CharField(widget=SignatureWidget, required=False)

    SIGNATURE_REQUIRED = _("Signature is required")
    SIGNATURE_CHANGE_FORBIDDEN = _(
        "Only patient or parent/guardian can change signature !"
    )
    SIGNATURE_INVALID = _("Invalid signature data !")

    def __init__(self, *args, **kwargs):
        if "registry_model" in kwargs:
            consent_config = getattr(
                kwargs["registry_model"], "consent_configuration", None
            )
            del kwargs["registry_model"]
        else:
            consent_config = None

        self.can_sign_consent = False
        if "can_sign_consent" in kwargs:
            self.can_sign_consent = kwargs["can_sign_consent"]
            del kwargs["can_sign_consent"]

        super().__init__(*args, **kwargs)

        self.signature_required = (
            consent_config
            and consent_config.signature_required
            and self.can_sign_consent
        )
        self.fields["signature"].required = self.signature_required

    def clean_signature(self):
        signature = self.cleaned_data["signature"]
        if not signature:
            if self.signature_required:
                raise ValidationError(self.SIGNATURE_REQUIRED, code="required")
            return signature
        try:
            data = json.loads(base64.b64decode(signature))["data"]
        except UnicodeDecodeError:
            raise ValidationError(self.SIGNATURE_INVALID)
        except binascii.Error:
            raise ValidationError(self.SIGNATURE_INVALID)
        if len(data) == 0:
            if self.signature_required:
                raise ValidationError(self.SIGNATURE_REQUIRED, code="required")
        elif not self.can_sign_consent:
            existing_data = []
            if self.instance and self.instance.signature:
                existing_data = json.loads(
                    base64.b64decode(self.instance.signature)
                )["data"]
            if data != existing_data:
                raise ValidationError(self.SIGNATURE_CHANGE_FORBIDDEN)

        return signature


class PatientStageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "instance" in kwargs and kwargs["instance"] is not None:
            self.instance = kwargs["instance"]
            stages_qs = PatientStage.objects.filter(
                registry=self.instance.registry
            )
            self.fields["allowed_prev_stages"].queryset = stages_qs
            self.fields["allowed_next_stages"].queryset = stages_qs
            self.fields["registry"].disabled = True

    def clean(self):
        cleaneddata = super().clean()
        if self.instance and hasattr(self.instance, "registry"):
            cleaneddata["registry"] = self.instance.registry
        prev_stages = cleaneddata["allowed_prev_stages"]
        next_stages = cleaneddata["allowed_next_stages"]
        selected_registry = cleaneddata["registry"]
        if not all(
            [stage.registry == selected_registry for stage in prev_stages]
        ):
            raise ValidationError(
                {
                    "allowed_prev_stages": [
                        _(
                            "All stages in prev stages must belong to the selected registry !"
                        )
                    ]
                }
            )
        if not all(
            [stage.registry == selected_registry for stage in next_stages]
        ):
            raise ValidationError(
                {
                    "allowed_next_stages": [
                        _(
                            "All stages in next stages must belong to the selected registry !"
                        )
                    ]
                }
            )
        return cleaneddata

    class Meta:
        model = PatientStage
        fields = "__all__"

    class Media:
        js = (
            "js/admin/registry_change_handler.js",
            "js/admin/patient_stage_admin.js",
        )


class PatientStageRuleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "instance" in kwargs and kwargs["instance"] is not None:
            instance = kwargs["instance"]
            stages_qs = PatientStage.objects.filter(registry=instance.registry)
            self.fields["from_stage"].queryset = stages_qs
            self.fields["to_stage"].queryset = stages_qs

    def clean(self):
        cleaneddata = self.cleaned_data
        from_stage = cleaneddata["from_stage"]
        to_stage = cleaneddata["to_stage"]
        if not from_stage and not to_stage:
            raise ValidationError(
                _("Both to_stage and from_stage cannot be None !")
            )
        if from_stage and from_stage.registry != cleaneddata["registry"]:
            raise ValidationError(
                {
                    "from_stage": [
                        _(
                            "The initial stage must belong to the selected registry !"
                        )
                    ]
                }
            )
        if to_stage and to_stage.registry != cleaneddata["registry"]:
            raise ValidationError(
                {
                    "to_stage": [
                        _(
                            "The final stage must belong to the selected registry !"
                        )
                    ]
                }
            )
        if (
            to_stage
            and from_stage
            and to_stage not in from_stage.allowed_next_stages.all()
        ):
            raise ValidationError(
                {
                    "to_stage": [
                        _(
                            "The final stage must be in the next stages list of the initial stage!"
                        )
                    ]
                }
            )

        return super().clean()

    class Meta:
        model = PatientStageRule
        fields = "__all__"

    class Media:
        js = (
            "js/admin/registry_change_handler.js",
            "js/admin/patient_stage_rule_admin.js",
        )


class PatientForm(forms.ModelForm):
    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    next_of_kin_country = forms.ChoiceField(
        required=False,
        widget=CountryWidget(attrs={"onChange": "select_country(this);"}),
        label=_("Next of kin country"),
    )
    next_of_kin_state = forms.ChoiceField(
        required=False, widget=StateWidget(), label=_("Next of kin state")
    )
    country_of_birth = forms.ChoiceField(
        required=False, widget=CountryWidget(), label=_("Country of birth")
    )

    def __init__(self, *args, **kwargs):
        def clinician_display_str(obj):
            title = obj.title or ""
            full_name = f"{obj.first_name} {obj.last_name}"
            wgs = ", ".join([wg.name for wg in obj.working_groups.all()])
            return f"{title} {full_name} ({wgs})"

        def has_displayable_working_groups(choices):
            if not choices:
                return False

            if len(choices) > 1:
                return True

            working_group_id, *_ = choices[0]
            return (
                working_group_id
                != WorkingGroup.objects.get_unallocated(
                    registry=self.registry_model
                ).id
            )

        instance = None

        if "registry_model" in kwargs:
            self.registry_model = kwargs["registry_model"]
            del kwargs["registry_model"]
        else:
            self.registry_model = None

        if "instance" in kwargs and kwargs["instance"] is not None:
            instance = kwargs["instance"]
            registry_specific_data = self._get_registry_specific_data(instance)
            wrapped_data = self._wrap_file_cdes(registry_specific_data)
            initial_data = kwargs.get("initial", {})
            for reg_code in wrapped_data:
                initial_data.update(wrapped_data[reg_code])

            self._update_initial_consent_data(instance, initial_data)

            kwargs["initial"] = initial_data

        if "user" in kwargs:
            self.user = kwargs.pop("user")

        if "carer" in kwargs:
            self.carer = kwargs.pop("carer")

        super().__init__(*args, **kwargs)

        if self.registry_model:
            if self.registry_model.has_feature(
                RegistryFeatures.CLINICIANS_HAVE_PATIENTS
            ):
                self.fields[
                    "registered_clinicians"
                ].queryset = CustomUser.objects.filter(
                    groups__name__iexact=GROUPS.CLINICAL
                )
                self.fields[
                    "registered_clinicians"
                ].label_from_instance = clinician_display_str

                if instance and instance.registered_clinicians.exists():
                    clinician_wgs = set(
                        [
                            wg
                            for c in instance.registered_clinicians.all()
                            for wg in c.working_groups.all()
                        ]
                    )
                    instance.working_groups.add(*clinician_wgs)
                    instance.wgs_set_by_clinicians = True
            else:
                self.fields[
                    "registered_clinicians"
                ].widget = forms.HiddenInput()

            if self.registry_model.has_feature(
                RegistryFeatures.PATIENTS_CREATE_USERS
            ):
                if instance and instance.user:
                    self.fields["email"].disabled = True

                    change_email_url = None
                    if instance.user == self.user:
                        change_email_url = reverse("email_address_change")
                    elif self.user.has_perm("patients.change_patientuser"):
                        change_email_url = reverse(
                            "patient_email_change",
                            kwargs={"patient_id": instance.id},
                        )

                    if change_email_url:
                        self.fields["email"].help_text = mark_safe(
                            f'<a href="{change_email_url}">{_("Change email address")}</a>'
                        )
                else:
                    self.fields["email"].required = True

        registries = Registry.objects.all()
        if self.registry_model:
            registries = registries.filter(id=self.registry_model.id)
        self.fields["rdrf_registry"].queryset = registries
        self.fields["rdrf_registry"].initial = [registries.first()]

        if hasattr(self, "user"):
            user = self.user
            # working groups shown should be only related to the groups avail to the
            # user in the registry being edited
            if self._is_parent_editing_child(instance):
                # see FKRP #472
                self.fields["working_groups"].widget = forms.SelectMultiple(
                    attrs={"readonly": "readonly"}
                )
                self.fields[
                    "working_groups"
                ].queryset = instance.working_groups.all()
            else:
                working_groups_choices, additional_working_group_fields = (
                    working_group_fields(
                        WorkingGroup.objects.filter(
                            registry=self.registry_model
                        ),
                        self.instance.working_groups.all()
                        if self.instance.id
                        else WorkingGroup.objects.none(),
                    )
                )
                self.fields.update(additional_working_group_fields)
                self.fields["working_groups"].choices = working_groups_choices
                if not has_displayable_working_groups(working_groups_choices):
                    self.fields["working_groups"].disabled = True
                    self.fields["working_groups"].required = False
                    self.fields[
                        "working_groups"
                    ].widget = forms.MultipleHiddenInput()

            # field visibility restricted no non admins
            if not user.is_superuser:
                registry = self.registry_model or user.registry.all()[0]
                user_groups = user.groups.all()

                def get_field_config(field):
                    qs = DemographicFields.objects.filter(
                        registry=registry, groups__in=user_groups, field=field
                    )
                    return qs.distinct().first()

                field_configs = [
                    fc
                    for fc in [get_field_config(field) for field in self.fields]
                    if fc is not None
                ]

                def apply_field_config(target_field, target_field_config):
                    if getattr(
                        self.fields[target_field].widget,
                        "allow_multiple_selected",
                        False,
                    ):
                        if (
                            target_field_config.status
                            == DemographicFields.HIDDEN
                        ):
                            self.fields[target_field].required = False
                            self.fields[
                                target_field
                            ].widget = forms.MultipleHiddenInput()
                        elif (
                            target_field_config.status
                            == DemographicFields.READONLY
                        ):
                            self.fields[target_field].required = False
                            self.fields[target_field].widget.attrs.update(
                                {"disabled": "disabled"}
                            )
                    else:
                        if (
                            target_field_config.status
                            == DemographicFields.HIDDEN
                        ):
                            self.fields[
                                target_field
                            ].widget = forms.HiddenInput()
                            self.fields[target_field].label = ""
                        elif (
                            target_field_config.status
                            == DemographicFields.READONLY
                        ):
                            self.fields[target_field].widget = forms.TextInput(
                                attrs={"readonly": "readonly"}
                            )

                for field_config in field_configs:
                    field = field_config.field
                    apply_field_config(field, field_config)
                    if field == "working_groups":
                        additional_working_group_fields = [
                            form_fields
                            for form_fields in self.fields
                            if form_fields.startswith("working_groups_")
                        ]
                        for wg_field in additional_working_group_fields:
                            apply_field_config(wg_field, field_config)

            if (
                not user.is_patient
                and self.registry_model
                and self.registry_model.has_feature(RegistryFeatures.STAGES)
            ):
                if "stage" in self.initial and self.initial["stage"]:
                    current_stage = PatientStage.objects.get(
                        pk=self.initial["stage"]
                    )

                    allowed_stages = chain(
                        current_stage.allowed_prev_stages.all(),
                        (current_stage,),
                        current_stage.allowed_next_stages.all(),
                    )

                    self.fields["stage"].queryset = PatientStage.objects.filter(
                        pk__in=(s.pk for s in allowed_stages)
                    )
                else:
                    self.fields["stage"].queryset = PatientStage.objects.filter(
                        allowed_prev_stages__isnull=True,
                        registry=self.registry_model,
                    )

        if self._is_adding_patient(kwargs):
            self._setup_add_form()

    def _is_parent_editing_child(self, patient_model):
        # see FKRP #472
        if patient_model is not None and hasattr(self, "user"):
            try:
                parent_guardian = ParentGuardian.objects.get(user=self.user)
                return patient_model in parent_guardian.children
            except ParentGuardian.DoesNotExist:
                pass

    def _get_registry_specific_data(self, patient_model):
        if patient_model is None:
            return {}
        mongo_wrapper = DynamicDataWrapper(patient_model)
        return mongo_wrapper.load_registry_specific_data(self.registry_model)

    def _wrap_file_cdes(self, registry_specific_data):
        from rdrf.forms.file_upload import FileUpload, is_filestorage_dict
        from rdrf.helpers.utils import is_file_cde

        def wrap_file_cde_dict(registry_code, cde_code, filestorage_dict):
            return FileUpload(registry_code, cde_code, filestorage_dict)

        def wrap(registry_code, cde_code, value):
            if is_file_cde(cde_code) and is_filestorage_dict(value):
                return wrap_file_cde_dict(registry_code, cde_code, value)
            else:
                return value

        wrapped_dict = {}

        for reg_code in registry_specific_data:
            reg_data = registry_specific_data[reg_code]
            wrapped_data = {
                key: wrap(reg_code, key, value)
                for key, value in reg_data.items()
            }
            wrapped_dict[reg_code] = wrapped_data

        return wrapped_dict

    def _update_initial_consent_data(self, patient_model, initial_data):
        if patient_model is None:
            return
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]

    def _is_adding_patient(self, kwargs):
        return "instance" in kwargs and kwargs["instance"] is None

    def _setup_add_form(self):
        if hasattr(self, "user"):
            user = self.user
        else:
            user = None

        if not user.is_superuser:
            self.fields[
                "working_groups"
            ].queryset = WorkingGroup.objects.get_by_user_and_registry(
                user, self.registry_model
            )
        else:
            self.fields[
                "working_groups"
            ].queryset = WorkingGroup.objects.filter(
                registry=self.registry_model
            )

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "datepicker"}, format="%d-%m-%Y"
        ),
        help_text=_("DD-MM-YYYY"),
        input_formats=["%d-%m-%Y"],
    )

    date_of_death = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "datepicker"}, format="%d-%m-%Y"
        ),
        help_text=_("DD-MM-YYYY"),
        input_formats=["%d-%m-%Y"],
        required=False,
    )

    date_of_migration = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "datepicker"}, format="%d-%m-%Y"
        ),
        help_text=_("DD-MM-YYYY"),
        required=False,
        input_formats=["%d-%m-%Y"],
    )

    class Meta:
        model = Patient
        widgets = {
            "next_of_kin_address": forms.Textarea(
                attrs={"rows": 3, "cols": 30}
            ),
            "inactive_reason": forms.Textarea(attrs={"rows": 3, "cols": 30}),
            "user": forms.HiddenInput(),
        }
        exclude = ["doctors", "user", "created_by", "carer"]

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean_rdrf_registry(self):
        registries = self.cleaned_data.get("rdrf_registry")
        if not registries:
            raise ValidationError("Patient must be added with a registry")
        return registries

    def clean_working_groups(self):
        is_base_working_groups_disabled = (
            "disabled" in self.fields["working_groups"].widget.attrs
            or self.fields["working_groups"].disabled
        )
        base_working_group_choices = self.fields["working_groups"].choices
        selected_working_group_ids = self.data.getlist("working_groups")

        additional_working_group_fields = [
            field_name
            for field_name in self.data.keys()
            if field_name.startswith("working_groups_")
        ]
        selected_additional_working_group_ids = [
            value
            for field_name in additional_working_group_fields
            for value in self.data.getlist(field_name)
        ]

        # Determine the base working groups the patient should have
        if is_base_working_groups_disabled:
            if not base_working_group_choices:
                working_groups = WorkingGroup.objects.none()
            else:
                unallocated_working_group = (
                    WorkingGroup.objects.get_unallocated(self.registry_model)
                )
                if selected_additional_working_group_ids:
                    # The patient has been assigned to additional working groups,
                    # and they can't otherwise select from the base working groups, so remove them from "Unallocated"
                    working_groups = WorkingGroup.objects.filter(
                        id__in=selected_working_group_ids
                    ).exclude(id=unallocated_working_group.id)
                elif self.instance.working_groups.exists():
                    # No working groups have been selected, (assume all working groups controls are disabled)
                    # so keep existing working groups
                    working_groups = self.instance.working_groups.all()
                else:
                    # The patient has no allocated working groups, set to "Unallocated"
                    working_groups = WorkingGroup.objects.filter(
                        id=unallocated_working_group.id
                    )
        else:
            working_groups = WorkingGroup.objects.filter(
                id__in=selected_working_group_ids
            )

        all_selected_working_groups = working_groups.union(
            WorkingGroup.objects.filter(
                id__in=selected_additional_working_group_ids
            )
        )
        if not all_selected_working_groups:
            raise forms.ValidationError(
                "Patient must be assigned to a working group"
            )
        return all_selected_working_groups

    def clean_registered_clinicians(self):
        reg = self.cleaned_data.get("rdrf_registry", Registry.objects.none())
        reg_clinicians = self.cleaned_data["registered_clinicians"]
        if reg and reg.exists():
            current_registry = reg.first()
            if (
                current_registry.has_feature(RegistryFeatures.CLINICIAN_FORM)
                and reg_clinicians.count() > 1
            ):
                raise ValidationError(_("You may only select one clinician"))
        return reg_clinicians

    def clean_email(self):
        registries = self.cleaned_data.get(
            "rdrf_registry", Registry.objects.none()
        )
        email = self.cleaned_data.get("email")

        if "email" in self.changed_data:
            for registry in registries:
                if registry.has_feature(RegistryFeatures.PATIENTS_CREATE_USERS):
                    if CustomUser.objects.filter(email__iexact=email).exists():
                        raise ValidationError(
                            _("User with this email already exists")
                        )
                    break

        if self.fields["email"].disabled:
            return self.instance.email
        else:
            return email

    def clean(self):
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]

        self._validate_custom_consents()
        return super().clean()

    def _validate_custom_consents(self):
        data = {}
        for field_key in self.custom_consents:
            parts = field_key.split("_")
            reg_pk = int(parts[1])
            registry_model = Registry.objects.get(id=reg_pk)
            if registry_model not in data:
                data[registry_model] = {}

            consent_section_pk = int(parts[2])
            consent_section_model = ConsentSection.objects.get(
                id=int(consent_section_pk)
            )

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(
                id=consent_question_pk
            )
            answer = self.custom_consents[field_key]
            data[registry_model][consent_section_model][
                consent_question_model.code
            ] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:
                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (
                        registry_model.code.upper(),
                        consent_section_model.section_label,
                    )
                    validation_errors.append(error_message)

        if len(validation_errors) > 0:
            raise forms.ValidationError(
                "Consent Error(s): %s" % ",".join(validation_errors)
            )

    def notify_clinicians(
        self, patient_model, existing_clinicians, current_clinicians
    ):
        from rdrf.events.events import EventType
        from rdrf.services.io.notifications.email_notification import (
            process_notification,
        )

        instance = getattr(self, "instance", None)
        registry_model = instance.rdrf_registry.first()

        new_clinicians = current_clinicians - existing_clinicians
        for c in new_clinicians:
            template_data = {"patient": patient_model, "clinician": c}
            process_notification(
                registry_model.code, EventType.CLINICIAN_ASSIGNED, template_data
            )
        removed_clinicians = existing_clinicians - current_clinicians
        for c in removed_clinicians:
            template_data = {"patient": patient_model, "clinician": c}
            process_notification(
                registry_model.code,
                EventType.CLINICIAN_UNASSIGNED,
                template_data,
            )

    def save(self, commit=True):
        patient_model = super(PatientForm, self).save(commit=False)
        patient_model.active = True
        try:
            patient_registries = [r for r in patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []

        if commit:
            instance = getattr(self, "instance", None)
            patient_model.save()
            existing_clinicians = set()
            if instance:
                existing_clinicians = set(instance.registered_clinicians.all())

            patient_model.working_groups.set(
                self.cleaned_data["working_groups"]
            )

            registries = self.cleaned_data["rdrf_registry"]
            for reg in registries:
                patient_model.rdrf_registry.add(reg)

            if any(
                [
                    r.has_feature(RegistryFeatures.CLINICIANS_HAVE_PATIENTS)
                    for r in registries
                ]
            ):
                current_clinicians = set(
                    self.cleaned_data["registered_clinicians"]
                )
                patient_model.registered_clinicians.set(current_clinicians)
                if patient_model.registered_clinicians.exists():
                    clinician_wgs = set(
                        [
                            wg
                            for c in patient_model.registered_clinicians.all()
                            for wg in c.working_groups.all()
                        ]
                    )
                    patient_model.working_groups.add(*clinician_wgs)
                self.notify_clinicians(
                    patient_model, existing_clinicians, current_clinicians
                )

            patient_model.save()

        for consent_field in self.custom_consents:
            registry_model, consent_section_model, consent_question_model = (
                self._get_consent_field_models(consent_field)
            )

            if registry_model in patient_registries:
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(
                        consent_question_model,
                        self.custom_consents[consent_field],
                        commit,
                    )
            if not patient_registries:
                closure = self._make_consent_closure(
                    registry_model,
                    consent_section_model,
                    consent_question_model,
                    consent_field,
                )
                if hasattr(patient_model, "add_registry_closures"):
                    patient_model.add_registry_closures.append(closure)
                else:
                    setattr(patient_model, "add_registry_closures", [closure])

        return patient_model

    def _make_consent_closure(
        self,
        registry_model,
        consent_section_model,
        consent_question_model,
        consent_field,
    ):
        def closure(patient_model, registry_ids):
            if registry_model.id in registry_ids:
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(
                        consent_question_model,
                        self.custom_consents[consent_field],
                    )
            else:
                pass

        return closure


class ParentAddPatientForm(forms.Form):
    first_name = forms.CharField(required=True, max_length=30)
    surname = forms.CharField(required=True, max_length=30)
    date_of_birth = forms.DateField(required=True)
    gender = forms.ChoiceField(
        choices=Patient.SEX_CHOICES, widget=forms.RadioSelect, required=True
    )
    use_parent_address = forms.BooleanField(required=False)
    address = forms.CharField(required=True, max_length=100)
    suburb = forms.CharField(required=True, max_length=30)
    country = forms.ChoiceField(
        required=True,
        widget=CountryWidget,
        choices=CountryWidget.choices(),
        initial="",
    )
    state = forms.CharField(required=True, widget=StateWidget)
    postcode = forms.CharField(required=True, max_length=30)

    def _clean_fields(self):
        base_required_fields = [
            "address",
            "suburb",
            "country",
            "state",
            "postcode",
        ]
        if self.data.get("use_parent_address", False):
            for f in base_required_fields:
                self.fields[f].required = False
        super()._clean_fields()


class ParentGuardianForm(forms.ModelForm):
    class Meta:
        model = ParentGuardian
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "address",
            "country",
            "state",
            "suburb",
            "postcode",
            "phone",
        ]
        exclude = ["user", "patient", "place_of_birth", "date_of_migration"]

        widgets = {"state": StateWidget(), "country": CountryWidget()}


class PatientUserForm(forms.ModelForm):
    def clean_user(self):
        user = self.cleaned_data.get("user")

        if user:
            # Check if any other patient is linked to this user
            user_patients = Patient.objects.filter(user=user).exclude(
                id=self.instance.id
            )
            if user_patients:
                raise ValidationError(
                    _("User is already linked to another patient")
                    + f" ({user_patients.first().display_name})"
                )

            # Check the user is a patient
            if not user.in_group(GROUPS.PATIENT):
                raise ValidationError(
                    _("User must be a member of the Patient group")
                )

            # Check the user is a member of all the registries the patient is
            user_registries = set(user.registry.all())
            patient_registries = set(self.instance.rdrf_registry.all())

            missing_registries = patient_registries.difference(user_registries)
            extra_registries = user_registries.difference(patient_registries)

            if missing_registries or extra_registries:
                registry_diff_error = _(
                    "User must belong to the same registries as the patient."
                )

                if missing_registries:
                    registry_diff_error += (
                        " "
                        + _("User's missing registries")
                        + ": "
                        + f'{", ".join(r.name for r in missing_registries)}.'
                    )

                if extra_registries:
                    registry_diff_error += (
                        " "
                        + _("User's extra registries")
                        + ": "
                        + f'{", ".join(r.name for r in extra_registries)}.'
                    )

                raise ValidationError(registry_diff_error)

        return user
