import base64
import binascii
from itertools import chain
import json
import logging

from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict

from .models import (
    Patient,
    PatientAddress,
    PatientConsent,
    Registry,
    PatientRelative,
    ParentGuardian,
    PatientDoctor,
    PatientStage,
    PatientSignature,
    PatientStageRule
)
from rdrf.db.dynamic_data import DynamicDataWrapper
from rdrf.models.definition.models import ConsentQuestion, ConsentSection, DemographicFields
from rdrf.forms.dynamic.fields import FileTypeRestrictedFileField
from rdrf.forms.widgets.widgets import CountryWidget, StateWidget, ConsentFileInput, SignatureWidget
from rdrf.helpers.registry_features import RegistryFeatures
from registry.groups.models import CustomUser, WorkingGroup
from registry.patients.patient_widgets import PatientRelativeLinkWidget
from django.utils.translation import gettext as _

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

    relationship = forms.ChoiceField(label=_("Type of Medical Professional"), choices=OPTIONS)

    class Meta:
        fields = "__all__"
        model = PatientDoctor


class PatientRelativeForm(forms.ModelForm):
    class Meta:
        model = PatientRelative
        fields = "__all__"  # Added after upgrading to Django 1.8
        # Added after upgrading to Django 1.8  - uniqueness check was failing
        # otherwise (RDR-1039)
        exclude = ['id']
        widgets = {
            'relative_patient': PatientRelativeLinkWidget,
        }

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'])

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
                value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
                if name == "relative_patient":
                    if value == "on":
                        self.cleaned_data[name] = None
                        self.create_patient_flag = True
                    else:
                        self.cleaned_data[name] = value

                elif name == 'date_of_birth':
                    try:
                        self.cleaned_data[name] = self._set_date_of_birth(value)
                    except Exception:
                        raise ValidationError("Date of Birth must be dd-mm-yyyy")

                elif name == 'patient':
                    continue  # this was causing error in post clean - we set this ourselves
                else:
                    self.cleaned_data[name] = value

            except ValidationError as e:
                num_errors += 1
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]

        self.tag = self.cleaned_data["given_names"] + self.cleaned_data["family_name"]

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
        fields = ('address_type', 'address', 'country', 'state', 'suburb', 'postcode')

    country = forms.ChoiceField(required=True,
                                widget=CountryWidget(attrs={'onChange': 'select_country(this);'}))
    state = forms.ChoiceField(required=True,
                              widget=StateWidget())
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class PatientConsentFileForm(forms.ModelForm):
    class Meta:
        model = PatientConsent
        fields = ["form"]
        exclude = ["filename"]

    form = FileTypeRestrictedFileField(widget=ConsentFileInput, required=False)

    def save(self, commit=True):
        # remember the filename of the uploaded file
        logger.debug("File Saved")
        if self.cleaned_data.get("form"):
            self.instance.filename = self.cleaned_data["form"].name
        return super(PatientConsentFileForm, self).save(commit)


class PatientSignatureForm(forms.ModelForm):
    class Meta:
        model = PatientSignature
        fields = ["signature"]

    signature = forms.CharField(widget=SignatureWidget, required=False)

    SIGNATURE_REQUIRED = _("Signature is required")
    SIGNATURE_CHANGE_FORBIDDEN = _("Only patient or parent/guardian can change signature !")
    SIGNATURE_INVALID = _("Invalid signature data !")

    def __init__(self, *args, **kwargs):
        if 'registry_model' in kwargs:
            consent_config = getattr(kwargs['registry_model'], 'consent_configuration', None)
            del kwargs['registry_model']
        else:
            consent_config = None

        self.can_sign_consent = False
        if 'can_sign_consent' in kwargs:
            self.can_sign_consent = kwargs['can_sign_consent']
            del kwargs['can_sign_consent']

        super().__init__(*args, **kwargs)

        self.signature_required = consent_config and consent_config.signature_required and self.can_sign_consent
        self.fields['signature'].required = self.signature_required

    def clean_signature(self):
        signature = self.cleaned_data['signature']
        if not signature:
            if self.signature_required:
                raise ValidationError(self.SIGNATURE_REQUIRED, code="required")
            return signature
        try:
            data = json.loads(base64.b64decode(signature))['data']
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
                existing_data = json.loads(base64.b64decode(self.instance.signature))['data']
            if data != existing_data:
                raise ValidationError(self.SIGNATURE_CHANGE_FORBIDDEN)

        return signature


class PatientStageForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance'] is not None:
            self.instance = kwargs['instance']
            stages_qs = PatientStage.objects.filter(registry=self.instance.registry)
            self.fields["allowed_prev_stages"].queryset = stages_qs
            self.fields["allowed_next_stages"].queryset = stages_qs
            self.fields["registry"].disabled = True

    def clean(self):
        cleaneddata = super().clean()
        if self.instance and hasattr(self.instance, 'registry'):
            cleaneddata["registry"] = self.instance.registry
        prev_stages = cleaneddata["allowed_prev_stages"]
        next_stages = cleaneddata["allowed_next_stages"]
        selected_registry = cleaneddata["registry"]
        if not all([stage.registry == selected_registry for stage in prev_stages]):
            raise ValidationError({
                "allowed_prev_stages": [_("All stages in prev stages must belong to the selected registry !")]
            })
        if not all([stage.registry == selected_registry for stage in next_stages]):
            raise ValidationError({
                "allowed_next_stages": [_("All stages in next stages must belong to the selected registry !")]
            })
        return cleaneddata

    class Meta:
        model = PatientStage
        fields = "__all__"

    class Media:
        js = ("js/admin/registry_change_handler.js", "js/admin/patient_stage_admin.js",)


class PatientStageRuleForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance'] is not None:
            instance = kwargs['instance']
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
            raise ValidationError({
                "from_stage": [_("The initial stage must belong to the selected registry !")]
            })
        if to_stage and to_stage.registry != cleaneddata["registry"]:
            raise ValidationError({
                "to_stage": [_("The final stage must belong to the selected registry !")]
            })
        if to_stage and from_stage and to_stage not in from_stage.allowed_next_stages.all():
            raise ValidationError({
                "to_stage": [_("The final stage must be in the next stages list of the initial stage!")]
            })

        return super().clean()

    class Meta:
        model = PatientStageRule
        fields = "__all__"

    class Media:
        js = ("js/admin/registry_change_handler.js", "js/admin/patient_stage_rule_admin.js", )


class PatientForm(forms.ModelForm):

    ADDRESS_ATTRS = {
        "rows": 3,
        "cols": 30,
    }

    next_of_kin_country = forms.ChoiceField(
        required=False,
        widget=CountryWidget(attrs={'onChange': 'select_country(this);'}),
        label=_("Next of kin country")
    )
    next_of_kin_state = forms.ChoiceField(
        required=False,
        widget=StateWidget(),
        label=_("Next of kin state")
    )
    country_of_birth = forms.ChoiceField(
        required=False,
        widget=CountryWidget(),
        label=_("Country of birth")
    )

    def __init__(self, *args, **kwargs):

        def clinician_display_str(obj):
            title = obj.title or ''
            full_name = f"{obj.first_name} {obj.last_name}"
            wgs = ', '.join([wg.name for wg in obj.working_groups.all()])
            return f"{title} {full_name} ({wgs})"

        registered_clinicians = CustomUser.objects.all()
        instance = None

        if 'registry_model' in kwargs:
            self.registry_model = kwargs['registry_model']
            del kwargs['registry_model']
        else:
            self.registry_model = None

        if 'instance' in kwargs and kwargs['instance'] is not None:
            instance = kwargs['instance']
            registry_specific_data = self._get_registry_specific_data(instance)
            wrapped_data = self._wrap_file_cdes(registry_specific_data)
            initial_data = kwargs.get('initial', {})
            for reg_code in wrapped_data:
                initial_data.update(wrapped_data[reg_code])

            self._update_initial_consent_data(instance, initial_data)

            kwargs['initial'] = initial_data

        if "user" in kwargs:
            self.user = kwargs.pop("user")

        if "carer" in kwargs:
            self.carer = kwargs.pop("carer")

        super().__init__(*args, **kwargs)

        registered_clinicians_filtered = [c.id for c in registered_clinicians if c.is_clinician]
        self.fields["registered_clinicians"].queryset = CustomUser.objects.filter(id__in=registered_clinicians_filtered)
        self.fields["registered_clinicians"].label_from_instance = clinician_display_str

        # registered_clinicians field should only be visible for registries which
        # support linking of patient to an "owning" clinician
        if self.registry_model:
            if not self.registry_model.has_feature(RegistryFeatures.CLINICIANS_HAVE_PATIENTS):
                self.fields["registered_clinicians"].widget = forms.HiddenInput()
            elif instance and instance.registered_clinicians.exists():
                clinician_wgs = set([wg for c in instance.registered_clinicians.all() for wg in c.working_groups.all()])
                instance.working_groups.add(*clinician_wgs)
                instance.wgs_set_by_clinicians = True
            if self.registry_model.has_feature(RegistryFeatures.PATIENTS_CREATE_USERS):
                self.fields["email"].required = True

        registries = Registry.objects.all()
        if self.registry_model:
            registries = registries.filter(id=self.registry_model.id)
        self.fields["rdrf_registry"].queryset = registries
        self.fields["rdrf_registry"].initial = [registries.first()]

        if hasattr(self, 'user'):
            user = self.user
            # working groups shown should be only related to the groups avail to the
            # user in the registry being edited
            if self._is_parent_editing_child(instance):
                # see FKRP #472
                self.fields["working_groups"].widget = forms.SelectMultiple(attrs={'readonly': 'readonly'})
                self.fields["working_groups"].queryset = instance.working_groups.all()
            else:
                self.fields["working_groups"].queryset = WorkingGroup.objects.filter(registry=self.registry_model)

            # field visibility restricted no non admins
            if not user.is_superuser:
                registry = self.registry_model or user.registry.all()[0]
                user_groups = user.groups.all()

                def get_field_config(field):
                    qs = DemographicFields.objects.filter(registry=registry, groups__in=user_groups, field=field)
                    return qs.distinct().first()

                field_configs = [fc for fc in [get_field_config(field) for field in self.fields] if fc is not None]

                for field_config in field_configs:
                    field = field_config.field
                    if getattr(self.fields[field].widget, 'allow_multiple_selected', False):
                        if field_config.status == DemographicFields.HIDDEN:
                            self.fields[field].widget = forms.MultipleHiddenInput()
                        elif field_config.status == DemographicFields.READONLY:
                            self.fields[field].required = False
                            self.fields[field].widget.attrs.update({'disabled': 'disabled'})
                    else:
                        if field_config.status == DemographicFields.HIDDEN:
                            self.fields[field].widget = forms.HiddenInput()
                            self.fields[field].label = ""
                        elif field_config.status == DemographicFields.READONLY:
                            self.fields[field].widget = forms.TextInput(attrs={'readonly': 'readonly'})

            if not user.is_patient and self.registry_model and self.registry_model.has_feature(RegistryFeatures.STAGES):
                if 'stage' in self.initial and self.initial['stage']:
                    current_stage = PatientStage.objects.get(pk=self.initial['stage'])

                    allowed_stages = chain(
                        current_stage.allowed_prev_stages.all(),
                        (current_stage, ),
                        current_stage.allowed_next_stages.all())

                    self.fields['stage'].queryset = PatientStage.objects.filter(pk__in=(s.pk for s in allowed_stages))
                else:
                    self.fields['stage'].queryset = PatientStage.objects.filter(
                        allowed_prev_stages__isnull=True, registry=self.registry_model
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
        from rdrf.forms.file_upload import FileUpload
        from rdrf.forms.file_upload import is_filestorage_dict
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
            wrapped_data = {key: wrap(reg_code, key, value) for key, value in reg_data.items()}
            wrapped_dict[reg_code] = wrapped_data

        return wrapped_dict

    def _update_initial_consent_data(self, patient_model, initial_data):
        if patient_model is None:
            return
        data = patient_model.consent_questions_data
        for consent_field_key in data:
            initial_data[consent_field_key] = data[consent_field_key]

    def _is_adding_patient(self, kwargs):
        return 'instance' in kwargs and kwargs['instance'] is None

    def _setup_add_form(self):
        if hasattr(self, "user"):
            user = self.user
        else:
            user = None

        if not user.is_superuser:
            initial_working_groups = user.working_groups.filter(registry=self.registry_model)
            self.fields['working_groups'].queryset = initial_working_groups
        else:
            self.fields['working_groups'].queryset = WorkingGroup.objects.filter(registry=self.registry_model)

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'])

    date_of_death = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        input_formats=['%d-%m-%Y'],
        required=False)

    date_of_migration = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}, format='%d-%m-%Y'),
        help_text=_("DD-MM-YYYY"),
        required=False,
        input_formats=['%d-%m-%Y'])

    class Meta:
        model = Patient
        widgets = {
            'next_of_kin_address': forms.Textarea(attrs={
                "rows": 3,
                "cols": 30
            }),
            'inactive_reason': forms.Textarea(attrs={
                "rows": 3,
                "cols": 30
            }),
            'user': forms.HiddenInput()
        }
        exclude = ['doctors', 'user', 'created_by', 'carer']

    # Added to ensure unique (familyname, givennames, workinggroup)
    # Does not need a unique constraint on the DB

    def clean_rdrf_registry(self):
        registries = self.cleaned_data.get("rdrf_registry")
        if not registries:
            raise ValidationError("Patient must be added with a registry")
        return registries

    def clean_working_groups(self):
        is_disabled = 'disabled' in self.fields['working_groups'].widget.attrs

        if is_disabled:
            return self.instance.working_groups.all()
        else:
            ret_val = self.cleaned_data["working_groups"]
            if not ret_val:
                raise forms.ValidationError("Patient must be assigned to a working group")
            return ret_val

    def clean_registered_clinicians(self):
        reg = self.cleaned_data.get("rdrf_registry", Registry.objects.none())
        reg_clinicians = self.cleaned_data["registered_clinicians"]
        if reg and reg.exists():
            current_registry = reg.first()
            if current_registry.has_feature(RegistryFeatures.CLINICIAN_FORM) and reg_clinicians.count() > 1:
                raise ValidationError(
                    _("You may only select one clinician")
                )
        return reg_clinicians

    def clean_email(self):
        registries = self.cleaned_data.get("rdrf_registry", Registry.objects.none())
        email = self.cleaned_data.get("email")

        # When patient is created or email is updated
        if "email" in self.changed_data:
            for registry in registries:
                if registry.has_feature(RegistryFeatures.PATIENTS_CREATE_USERS):
                    if CustomUser.objects.filter(email=email).first():
                        raise ValidationError(
                            _("User with this email already exists")
                        )
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
            consent_section_model = ConsentSection.objects.get(id=int(consent_section_pk))

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=consent_question_pk)
            answer = self.custom_consents[field_key]
            data[registry_model][consent_section_model][consent_question_model.code] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:

                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (registry_model.code.upper(),
                                                                              consent_section_model.section_label)
                    validation_errors.append(error_message)

        if len(validation_errors) > 0:
            raise forms.ValidationError("Consent Error(s): %s" % ",".join(validation_errors))

    def notify_clinicians(self, patient_model, existing_clinicians, current_clinicians):
        from rdrf.services.io.notifications.email_notification import process_notification
        from rdrf.events.events import EventType

        instance = getattr(self, 'instance', None)
        registry_model = instance.rdrf_registry.first()

        new_clinicians = current_clinicians - existing_clinicians
        for c in new_clinicians:
            template_data = {"patient": patient_model, "clinician": c}
            process_notification(registry_model.code, EventType.CLINICIAN_ASSIGNED, template_data)
        removed_clinicians = existing_clinicians - current_clinicians
        for c in removed_clinicians:
            template_data = {"patient": patient_model, "clinician": c}
            process_notification(registry_model.code, EventType.CLINICIAN_UNASSIGNED, template_data)

    def save(self, commit=True):
        patient_model = super(PatientForm, self).save(commit=False)
        patient_model.active = True
        try:
            patient_registries = [r for r in patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []

        if commit:
            instance = getattr(self, 'instance', None)
            patient_model.save()
            existing_clinicians = set()
            if instance:
                existing_clinicians = set(instance.registered_clinicians.all())

            patient_model.working_groups.set(self.cleaned_data["working_groups"])

            registries = self.cleaned_data["rdrf_registry"]
            for reg in registries:
                patient_model.rdrf_registry.add(reg)

            if any([r.has_feature(RegistryFeatures.CLINICIANS_HAVE_PATIENTS) for r in registries]):
                current_clinicians = set(self.cleaned_data["registered_clinicians"])
                patient_model.registered_clinicians.set(current_clinicians)
                if patient_model.registered_clinicians.exists():
                    clinician_wgs = set(
                        [wg for c in patient_model.registered_clinicians.all() for wg in c.working_groups.all()])
                    patient_model.working_groups.add(*clinician_wgs)
                self.notify_clinicians(patient_model, existing_clinicians, current_clinicians)

            patient_model.save()

        for consent_field in self.custom_consents:
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(
                consent_field)

            if registry_model in patient_registries:
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(consent_question_model, self.custom_consents[consent_field], commit)
            if not patient_registries:
                closure = self._make_consent_closure(registry_model, consent_section_model, consent_question_model,
                                                     consent_field)
                if hasattr(patient_model, 'add_registry_closures'):
                    patient_model.add_registry_closures.append(closure)
                else:
                    setattr(patient_model, 'add_registry_closures', [closure])

        return patient_model

    def _make_consent_closure(self, registry_model, consent_section_model, consent_question_model, consent_field):
        def closure(patient_model, registry_ids):
            if registry_model.id in registry_ids:
                if consent_section_model.applicable_to(patient_model):
                    patient_model.set_consent(consent_question_model, self.custom_consents[consent_field])
            else:
                pass

        return closure


class ParentAddPatientForm(forms.Form):
    first_name = forms.CharField(required=True, max_length=30)
    surname = forms.CharField(required=True, max_length=30)
    date_of_birth = forms.DateField(required=True)
    gender = forms.ChoiceField(choices=Patient.SEX_CHOICES, widget=forms.RadioSelect, required=True)
    use_parent_address = forms.BooleanField(required=False)
    address = forms.CharField(required=True, max_length=100)
    suburb = forms.CharField(required=True, max_length=30)
    country = forms.ChoiceField(required=True, widget=CountryWidget, choices=CountryWidget.choices(), initial="")
    state = forms.CharField(required=True, widget=StateWidget)
    postcode = forms.CharField(required=True, max_length=30)

    def _clean_fields(self):
        base_required_fields = ['address', 'suburb', 'country', 'state', 'postcode']
        if self.data.get('use_parent_address', False):
            for f in base_required_fields:
                self.fields[f].required = False
        super()._clean_fields()


class ParentGuardianForm(forms.ModelForm):
    class Meta:
        model = ParentGuardian
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'address', 'country', 'state', 'suburb', 'postcode',
            'phone'
        ]
        exclude = ['user', 'patient', 'place_of_birth', 'date_of_migration']

        widgets = {'state': StateWidget(), 'country': CountryWidget()}
