from collections import OrderedDict

from django.shortcuts import render, redirect
from django.views.generic.base import View
from django.views.generic import CreateView
from django.urls import reverse
from django.http import HttpResponseRedirect

from rdrf.models.definition.models import Registry, RegistryFeatures
from rdrf.models.definition.models import CdePolicy
from rdrf.helpers.utils import consent_status_for_patient

from django.forms.models import inlineformset_factory
from django.utils.html import strip_tags

from registry.patients.models import ParentGuardian
from registry.patients.models import Patient
from registry.patients.models import PatientAddress
from registry.patients.models import PatientDoctor
from registry.patients.models import PatientRelative
from registry.patients.admin_forms import PatientAddressForm
from registry.patients.admin_forms import PatientDoctorForm
from registry.patients.admin_forms import PatientForm
from registry.patients.admin_forms import PatientRelativeForm
from django.utils.translation import ugettext as _

from rdrf.forms.dynamic.registry_specific_fields import RegistrySpecificFieldsHandler
from rdrf.helpers.utils import get_error_messages
from rdrf.forms.navigation.wizard import NavigationWizard, NavigationFormType
from rdrf.forms.components import RDRFContextLauncherComponent
from rdrf.forms.components import RDRFPatientInfoComponent
from rdrf.forms.components import FamilyLinkagePanel
from rdrf.db.contexts_api import RDRFContextManager

from rdrf.security.security_checks import security_check_user_patient
from django.core.exceptions import PermissionDenied


import logging
logger = logging.getLogger(__name__)


class PatientFormMixin:
    original_form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    def __init__(self, *args, **kwargs):
        super(PatientFormMixin, self).__init__(*args, **kwargs)
        self.user = None   # filled in via get or post
        self.registry_model = None
        self.patient_form = None  # created via get_form
        self.patient_model = None
        self.object = None
        self.request = None   # set in post so RegistrySpecificFieldsHandler can process files

    # common methods

    def _get_registry_specific_fields(self, user, registry_model):
        """
        :param user:
        :param registry_model:
        :return: list of cde_model, field_object pairs
        """
        if user.is_superuser:
            return registry_model.patient_fields

        if registry_model not in user.registry.all():
            return []
        else:
            return registry_model.patient_fields

    def get_form_class(self):
        if not self.registry_model.patient_fields:
            return self.original_form_class

        form_class = self._create_registry_specific_patient_form_class(self.user,
                                                                       self.original_form_class,
                                                                       self.registry_model)
        return form_class

    def _set_registry_model(self, registry_code):
        self.registry_model = Registry.objects.get(code=registry_code)

    def get_success_url(self):
        """
        After a successful add where to go?
        Returns the supplied success URL. (We override to redirect to edit screen for the newly added patient)
        """
        registry_code = self.registry_model.code
        patient_id = self.object.pk
        patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id])
        return '%s?just_created=True' % patient_edit_url

    def _get_initial_context(self, registry_code, patient_model):
        from rdrf.models.definition.models import Registry
        registry_model = Registry.objects.get(code=registry_code)
        rdrf_context_manager = RDRFContextManager(registry_model)
        return rdrf_context_manager.get_or_create_default_context(
            patient_model, new_patient=True)

    def set_patient_model(self, patient_model):
        self.patient_model = patient_model

    def _set_user(self, request):
        self.user = request.user

    def _create_registry_specific_patient_form_class(
            self, user, form_class, registry_model, patient=None):
        additional_fields = OrderedDict()
        field_pairs = self._get_registry_specific_fields(user, registry_model)

        for cde, field_object in field_pairs:
            try:
                cde_policy = CdePolicy.objects.get(registry=registry_model, cde=cde)
            except CdePolicy.DoesNotExist:
                cde_policy = None

            if cde_policy is None or patient is None:
                additional_fields[cde.code] = field_object
            else:
                if user.is_superuser or cde_policy.is_allowed(user.groups.all(), patient):
                    if patient and patient.is_index:
                        additional_fields[cde.code] = field_object

        if len(list(additional_fields.keys())) == 0:
            additional_fields["HIDDEN"] = True
        else:
            additional_fields["HIDDEN"] = False

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_section_fields(self, user, registry_model):
        field_pairs = self._get_registry_specific_fields(user, registry_model)
        fieldset_title = registry_model.specific_fields_section_title
        field_list = [pair[0].code for pair in field_pairs]
        return fieldset_title, field_list

    def get_form(self, form_class=None):
        """
        PatientFormMixin.get_form Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()

        form_instance = super(PatientFormMixin, self).get_form(form_class)
        self.patient_form = form_instance
        return form_instance

    def get_context_data(self, **kwargs):
        """
        :param kwargs: The kwargs supplied to render to response
        :return:
        """
        patient_id = self._get_patient_id()
        patient_address_formset = kwargs.get("patient_address_formset", None)
        patient_doctor_formset = kwargs.get("patient_doctor_formset", None)
        patient_relative_formset = kwargs.get("patient_relative_formset", None)

        patient, forms_sections = self._get_patient_and_forms_sections(patient_id,
                                                                       self.registry_model.code,
                                                                       self.request,
                                                                       self.patient_form,
                                                                       patient_address_form=patient_address_formset,
                                                                       patient_doctor_form=patient_doctor_formset,
                                                                       patient_relative_form=patient_relative_formset)

        error_messages = get_error_messages([pair[0] for pair in forms_sections])

        num_errors = len(error_messages)
        kwargs["forms"] = forms_sections
        kwargs["patient"] = patient
        # Avoid spurious errors message when we first hit the Add screen:
        kwargs["errors"] = True if num_errors > 0 and any(
            [not form[0].is_valid() for form in forms_sections]) else False

        if "all_errors" in kwargs:
            kwargs["errors"] = True
            kwargs["error_messages"] = kwargs["all_errors"]
        else:
            kwargs["error_messages"] = error_messages
        kwargs["registry_code"] = self.registry_model.code
        kwargs["location"] = _("Demographics")
        section_blacklist = self._check_for_blacklisted_sections(self.registry_model)
        kwargs["section_blacklist"] = section_blacklist

        section_hiddenlist = self._check_for_hidden_section(self.request.user,
                                                            self.registry_model,
                                                            forms_sections)
        kwargs["section_hiddenlist"] = section_hiddenlist
        if self.request.user.is_parent:
            kwargs['parent'] = ParentGuardian.objects.get(user=self.request.user)
        return kwargs

    def _extract_error_messages(self, form_pairs):
        # forms is a list of (form, field_info_list) pairs
        error_messages = []
        for form, info in form_pairs:
            if not form.is_valid():
                for error in form.errors:
                    error_messages.append(form.errors[error])
        return list(map(strip_tags, error_messages))

    def _get_patient_id(self):
        if self.object:
            return self.object.pk
        else:
            return None

    def get_form_sections(self, user, request, patient, registry, registry_code, patient_form,
                          patient_address_form, patient_doctor_form, patient_relative_form):
        personal_header = _('Patients Personal Details')
        # shouldn't be hardcoding behaviour here plus the html formatting
        # originally here was not being passed as text
        if registry_code == "fkrp":
            personal_header += " " + \
                _("Here you can find an overview of all your personal and contact details you have given us. You can update your contact details by changing the information below.")

        personal_details_fields = (personal_header, [
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
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
            "living_status",
        ])

        next_of_kin = (_("Next of Kin"), [
            "next_of_kin_family_name",
            "next_of_kin_given_names",
            "next_of_kin_relationship",
            "next_of_kin_address",
            "next_of_kin_suburb",
            "next_of_kin_country",
            "next_of_kin_state",
            "next_of_kin_postcode",
            "next_of_kin_home_phone",
            "next_of_kin_mobile_phone",
            "next_of_kin_work_phone",
            "next_of_kin_email",
            "next_of_kin_parent_place_of_birth"
        ])

        rdrf_registry = (_("Registry"), [
            "rdrf_registry",
            "working_groups",
            "clinician"
        ])

        patient_address_section = (_("Patient Address"), None)

        patient_stage_section = (_("Patient Stage"), [
            "stage"
        ])

        form_sections = [
            (
                patient_form,
                (rdrf_registry,)
            ),
            (
                patient_form,
                (personal_details_fields,)
            ),
            (
                patient_address_form,
                (patient_address_section,)
            ),
            (
                patient_form,
                (next_of_kin,)
            ),
        ]
        if not user.is_patient and registry.has_feature(RegistryFeatures.STAGES):
            form_sections.append((
                patient_form,
                (patient_stage_section, )
            ))

        if registry.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            form_sections = form_sections[:-1]

        if registry.has_feature(RegistryFeatures.PATIENT_FORM_DOCTORS):
            if not patient_doctor_form:
                patient_doctor_formset = inlineformset_factory(Patient, Patient.doctors.through,
                                                               form=PatientDoctorForm,
                                                               extra=0,
                                                               can_delete=True,
                                                               fields="__all__")

                patient_doctor_form = patient_doctor_formset(
                    instance=patient, prefix="patient_doctor")

            patient_doctor_section = (_("Patient Doctor"), None)

            form_sections.append((
                patient_doctor_form,
                (patient_doctor_section,)
            ))

        # PatientRelativeForm for FH (only)
        has_family_linkage = registry.has_feature(RegistryFeatures.FAMILY_LINKAGE)
        include_patient_relative_section = (
            (has_family_linkage and not patient) or (has_family_linkage and patient and patient.is_index)
        )
        if include_patient_relative_section:
            if not patient_relative_form:
                patient_relative_formset = inlineformset_factory(Patient,
                                                                 PatientRelative,
                                                                 fk_name='patient',
                                                                 form=PatientRelativeForm,
                                                                 extra=0,
                                                                 can_delete=True,
                                                                 fields="__all__")

                patient_relative_form = patient_relative_formset(
                    instance=patient, prefix="patient_relative")

            patient_relative_section = (_("Patient Relative"), None)

            form_sections.append((patient_relative_form, (patient_relative_section,)))

        if registry.patient_fields:
            registry_specific_section_fields = self._get_registry_specific_section_fields(
                user, registry)
            form_sections.append(
                (patient_form, (registry_specific_section_fields,))
            )

        return form_sections

    def _get_patient_and_forms_sections(self,
                                        patient_id,
                                        registry_code,
                                        request,
                                        patient_form=None,
                                        patient_address_form=None,
                                        patient_doctor_form=None,
                                        patient_relative_form=None):

        user = request.user
        if patient_id is None:
            patient = None
        else:
            patient = Patient.objects.get(id=patient_id)

        registry = Registry.objects.get(code=registry_code)

        if not patient_form:
            if not registry.patient_fields:
                patient_form = PatientForm(instance=patient, user=user, registry_model=registry)
            else:
                munged_patient_form_class = self._create_registry_specific_patient_form_class(
                    user, PatientForm, registry, patient
                )
                patient_form = munged_patient_form_class(
                    instance=patient, user=user, registry_model=registry)

        patient_form.user = user

        if not patient_address_form:
            patient_address_formset = inlineformset_factory(Patient,
                                                            PatientAddress,
                                                            form=PatientAddressForm,
                                                            extra=0,
                                                            can_delete=True,
                                                            fields="__all__")

            patient_address_form = patient_address_formset(
                instance=patient, prefix="patient_address")

        form_sections = self.get_form_sections(
            user, request, patient, registry, registry_code, patient_form, patient_address_form,
            patient_doctor_form, patient_relative_form
        )

        return patient, form_sections

    def get_form_kwargs(self):
        kwargs = super(PatientFormMixin, self).get_form_kwargs()
        # NB This means we must be mixed in with a View ( which we are)
        kwargs["user"] = self.request.user
        kwargs["registry_model"] = self.registry_model
        return kwargs

    def all_forms_valid(self, forms):
        # called _after_ all form(s) validated
        # save patient
        patient_form = forms['patient_form']
        self.object = patient_form.save()
        # if this patient was created from a patient relative, sync with it
        self.object.sync_patient_relative()

        # save registry specific fields
        registry_specific_fields_handler = RegistrySpecificFieldsHandler(
            self.registry_model, self.object)

        registry_specific_fields_handler.save_registry_specific_data_in_mongo(self.request)

        # save addresses
        address_formset = forms.get('address_form')
        if address_formset:
            address_formset.instance = self.object
            address_formset.save()

        # save doctors
        if self.registry_model.has_feature(RegistryFeatures.PATIENT_FORM_DOCTORS):
            doctor_formset = forms.get('doctors_form')
            if doctor_formset:
                doctor_formset.instance = self.object
                doctor_formset.save()

        # patient relatives
        patient_relative_formset = forms.get('patient_relatives_form')
        if patient_relative_formset:
            patient_relative_formset.instance = self.object
            patient_relative_models = patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = self.object
                patient_relative_model.save()
                patient_relative_model.sync_relative_patient()
                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        if form.create_patient_flag:
                            patient_relative_model.create_patient_from_myself(
                                self.registry_model,
                                self.object.working_groups.all())

        return HttpResponseRedirect(self.get_success_url())

    def _run_consent_closures(self, patient_model, registry_ids):
        if hasattr(patient_model, "add_registry_closures"):
            for closure in patient_model.add_registry_closures:
                closure(patient_model, registry_ids)
            delattr(patient_model, 'add_registry_closures')

    def form_invalid(self, forms,
                     errors):
        has_errors = len(errors) > 0
        return self.render_to_response(
            self.get_context_data(
                form=forms['patient_form'],
                all_errors=errors,
                errors=has_errors,
                patient_address_formset=forms.get('address_form'),
                patient_doctor_formset=forms.get('doctors_form'),
                patient_relative_formset=forms.get('patient_relatives_form')
            )
        )

    def _get_address_formset(self, request, instance=None):
        patient_address_form_set = inlineformset_factory(
            Patient, PatientAddress, form=PatientAddressForm, fields="__all__")
        return patient_address_form_set(request.POST, instance=instance, prefix="patient_address")

    def _get_doctor_formset(self, request, instance=None):
        patient_doctor_form_set = inlineformset_factory(
            Patient, PatientDoctor, form=PatientDoctorForm, fields="__all__")
        return patient_doctor_form_set(request.POST, instance=instance, prefix="patient_doctor")

    def _get_patient_relatives_formset(self, request, instance=None):
        patient_relatives_formset = inlineformset_factory(Patient,
                                                          PatientRelative,
                                                          fk_name='patient',
                                                          form=PatientRelativeForm,
                                                          extra=0,
                                                          can_delete=True,
                                                          fields="__all__")

        return patient_relatives_formset(request.POST, instance=instance, prefix="patient_relative")

    def _has_doctors_form(self):
        return self.registry_model.has_feature(RegistryFeatures.PATIENT_FORM_DOCTORS)

    def _has_patient_relatives_form(self):
        return self.registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE)

    def get_forms(self, request, registry_model, user, instance=None):
        forms = OrderedDict()
        if not instance:
            patient_form_class = self.get_form_class()
            patient_form = self.get_form(patient_form_class)
        else:
            if registry_model.patient_fields:
                patient_form_class = self._create_registry_specific_patient_form_class(
                    user, PatientForm, registry_model, instance)
            else:
                patient_form_class = PatientForm

            patient_form = patient_form_class(
                request.POST,
                request.FILES,
                instance=instance,
                user=request.user,
                registry_model=registry_model)

        country_code = request.POST.get('country_of_birth')
        patient_form.fields['country_of_birth'].choices = [(country_code, country_code)]

        kin_country_code = request.POST.get('next_of_kin_country')
        kin_state_code = request.POST.get('next_of_kin_state')
        patient_form.fields['next_of_kin_country'].choices = [(kin_country_code, kin_country_code)]
        patient_form.fields['next_of_kin_state'].choices = [(kin_state_code, kin_state_code)]

        forms['patient_form'] = patient_form

        address_formset = self._get_address_formset(request, instance)
        index = 0
        for f in address_formset.forms:
            country_field_name = 'patient_address-' + str(index) + '-country'
            patient_country_code = request.POST.get(country_field_name)
            state_field_name = 'patient_address-' + str(index) + '-state'
            patient_state_code = request.POST.get(state_field_name)
            index += 1
            f.fields['country'].choices = [(patient_country_code, patient_country_code)]
            f.fields['state'].choices = [(patient_state_code, patient_state_code)]
        forms['address_form'] = address_formset

        if self._has_doctors_form():
            doctor_formset = self._get_doctor_formset(request)
            forms['doctors_form'] = doctor_formset

        if self._has_patient_relatives_form():
            patient_relative_formset = self._get_patient_relatives_formset(request)
            forms['patient_relatives_form'] = patient_relative_formset

        return forms

    def _section_fields_hidden(self, user, registry, fieldlist):
        from rdrf.models.definition.models import DemographicFields
        user_groups = [g.name for g in user.groups.all()]
        hidden_fields = DemographicFields.objects.filter(field__in=fieldlist,
                                                         registry=registry,
                                                         groups__name__in=user_groups,
                                                         hidden=True)

        return len(fieldlist) == hidden_fields.count()

    def _section_hidden(self, user, registry, section_name):
        from rdrf.models.definition.models import DemographicFields
        user_groups = [g.name for g in user.groups.all()]
        hidden_fields = DemographicFields.objects.filter(field=f"{DemographicFields.SECTION_PREFIX}{section_name}",
                                                         registry=registry,
                                                         groups__name__in=user_groups,
                                                         is_section=True,
                                                         hidden=True)

        return hidden_fields.exists()

    def _check_for_hidden_section(self, user, registry, form_sections):
        section_hiddenlist = []
        for form, sections in form_sections:
            for name, section in sections:
                if section is not None:
                    if self._section_fields_hidden(user, registry, section):
                        section_hiddenlist.append(name)
                if self._section_hidden(user, registry, name) and name not in section_hiddenlist:
                    section_hiddenlist.append(name)
        return section_hiddenlist

    def _check_for_blacklisted_sections(self, registry_model):
        if "section_blacklist" in registry_model.metadata:
            section_blacklist = registry_model.metadata["section_blacklist"]
            section_blacklist = [_(x) for x in section_blacklist]
        else:
            section_blacklist = []

        return section_blacklist


class AddPatientView(PatientFormMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'rdrf_cdes/generic_patient.html'

    def get(self, request, registry_code):
        if not request.user.is_authenticated:
            patient_add_url = reverse('patient_add', args=[registry_code])
            login_url = reverse('two_factor:login')
            return redirect("%s?next=%s" % (login_url, patient_add_url))

        self._set_registry_model(registry_code)
        self._set_user(request)
        return super(AddPatientView, self).get(request, registry_code)

    def post(self, request, registry_code):
        self.request = request
        self._set_user(request)
        self._set_registry_model(registry_code)
        forms = self.get_forms(request, self.registry_model, self.user)

        if all([form.is_valid() for form in forms.values() if form]):
            return self.all_forms_valid(forms)
        else:
            errors = get_error_messages([form for form in forms.values() if form])
            return self.form_invalid(forms, errors=errors)


class PatientEditView(PatientFormMixin, View):

    def get(self, request, registry_code, patient_id):
        if not request.user.is_authenticated:
            patient_edit_url = reverse('patient_edit', args=[registry_code, patient_id, ])
            login_url = reverse('two_factor:login')
            return redirect("%s?next=%s" % (login_url, patient_edit_url))

        registry_model = Registry.objects.get(code=registry_code)

        section_blacklist = self._check_for_blacklisted_sections(registry_model)

        patient, form_sections = self._get_patient_and_forms_sections(
            patient_id, registry_code, request)

        security_check_user_patient(request.user, patient)

        if registry_model.has_feature(RegistryFeatures.CONSENT_CHECKS):
            from rdrf.helpers.utils import consent_check
            if not consent_check(registry_model,
                                 request.user,
                                 patient,
                                 "see_patient"):
                raise PermissionDenied

        context_launcher = RDRFContextLauncherComponent(request.user, registry_model, patient)
        patient_info = RDRFPatientInfoComponent(registry_model, patient)

        family_linkage_panel = FamilyLinkagePanel(request.user,
                                                  registry_model,
                                                  patient)

        context = {
            "location": "Demographics",
            "context_launcher": context_launcher.html,
            "patient_info": patient_info.html,
            "forms": form_sections,
            "family_linkage_panel": family_linkage_panel.html,
            "patient": patient,
            "proms_link": self._get_proms_link(registry_model, patient),
            "patient_id": patient.id,
            "registry_code": registry_code,
            "form_links": [],
            "show_archive_button": request.user.can_archive,
            "archive_patient_url": patient.get_archive_url(registry_model) if request.user.can_archive else "",
            "consent": consent_status_for_patient(
                registry_code,
                patient),
            "section_blacklist": section_blacklist}
        if request.GET.get('just_created', False):
            context["message"] = _("Patient added successfully")

        context["not_linked"] = not patient.is_linked

        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient,
                                  NavigationFormType.DEMOGRAPHICS,
                                  None,
                                  None)

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        hidden_sectionlist = self._check_for_hidden_section(request.user,
                                                            registry_model,
                                                            form_sections)
        context["hidden_sectionlist"] = hidden_sectionlist

        return render(request, 'rdrf_cdes/patient_edit.html', context)

    def _get_proms_link(self, registry_model, patient_model):
        if not registry_model.has_feature(RegistryFeatures.PROMS_CLINICAL):
            return None
        return "todo"

    def post(self, request, registry_code, patient_id):
        user = request.user
        patient = Patient.objects.get(id=patient_id)
        security_check_user_patient(user, patient)

        actions = []

        registry_model = Registry.objects.get(code=registry_code)
        self.registry_model = registry_model

        context_launcher = RDRFContextLauncherComponent(request.user, registry_model, patient)
        patient_info = RDRFPatientInfoComponent(registry_model, patient)

        forms = self.get_forms(request, registry_model, user, patient)

        valid_forms = []
        error_messages = []

        for form in forms.values():
            if form and not form.is_valid():
                valid_forms.append(False)
                if isinstance(form.errors, list):
                    for error_dict in form.errors:
                        for field in error_dict:
                            error_messages.append("%s: %s" % (field, error_dict[field]))
                else:
                    for field in form.errors:
                        for error in form.errors[field]:
                            error_messages.append(error)
            else:
                valid_forms.append(True)

        if registry_model.has_feature(RegistryFeatures.PATIENT_FORM_DOCTORS):
            doctors_to_save = self._get_doctor_formset(request, patient)
            valid_forms.append(doctors_to_save.is_valid())

        patient_relatives_form = None
        if all(valid_forms):
            self.all_forms_valid(forms)
            patient, form_sections = self._get_patient_and_forms_sections(
                patient_id, registry_code, request)
            context = {
                "forms": form_sections,
                "patient": patient,
                "context_launcher": context_launcher.html,
                "message": _("Patient's details saved successfully"),
                "error_messages": [],
            }
        else:
            error_messages = get_error_messages([form for form in forms.values() if form])
            if not registry_model.has_feature(RegistryFeatures.PATIENT_FORM_DOCTORS):
                doctors_to_save = None
            patient, form_sections = self._get_patient_and_forms_sections(patient_id,
                                                                          registry_code,
                                                                          request,
                                                                          forms.get('patient_form'),
                                                                          forms.get('address_form'),
                                                                          doctors_to_save,
                                                                          patient_relatives_form)

            context = {
                "forms": form_sections,
                "patient": patient,
                "actions": actions,
                "context_launcher": context_launcher.html,
                "errors": True,
                "error_messages": error_messages,
            }

        wizard = NavigationWizard(request.user,
                                  registry_model,
                                  patient,
                                  NavigationFormType.DEMOGRAPHICS,
                                  None,
                                  None)

        family_linkage_panel = FamilyLinkagePanel(request.user,
                                                  registry_model,
                                                  patient)

        context["next_form_link"] = wizard.next_link
        context["previous_form_link"] = wizard.previous_link
        context["patient_info"] = patient_info.html

        context["registry_code"] = registry_code
        context["patient_id"] = patient.id
        context["location"] = _("Demographics")
        context["form_links"] = []
        context["not_linked"] = not patient.is_linked
        context["family_linkage_panel"] = family_linkage_panel.html
        context["show_archive_button"] = request.user.can_archive
        context["archive_patient_url"] = patient.get_archive_url(
            registry_model) if request.user.can_archive else ""
        context["consent"] = consent_status_for_patient(registry_code, patient)

        section_blacklist = self._check_for_blacklisted_sections(registry_model)
        context["section_blacklist"] = section_blacklist

        hidden_sectionlist = self._check_for_hidden_section(request.user,
                                                            registry_model,
                                                            form_sections)
        context["hidden_sectionlist"] = hidden_sectionlist

        if request.user.is_parent:
            context['parent'] = ParentGuardian.objects.get(user=request.user)

        return render(request, 'rdrf_cdes/patient_edit.html', context)

    def _is_linked(self, registry_model, patient_model):
        # is this patient linked to others?
        if not registry_model.has_feature(RegistryFeatures.FAMILY_LINKAGE):
            return False

        if not patient_model.is_index:
            return False

        for patient_relative in patient_model.relatives.all():
            if patient_relative.relative_patient:
                return True

        return False

    def create_patient_relatives(self, patient_relative_formset, patient_model, registry_model):
        if patient_relative_formset:
            patient_relative_formset.instance = patient_model
            patient_relative_models = patient_relative_formset.save()
            for patient_relative_model in patient_relative_models:
                patient_relative_model.patient = patient_model
                patient_relative_model.save()
                # explicitly synchronise with the patient that has already been created from
                # this patient relative ( if any )
                # to avoid infinite loops we are doing this explicitly in the views ( not
                # overriding save)
                patient_relative_model.sync_relative_patient()

                tag = patient_relative_model.given_names + patient_relative_model.family_name
                # The patient relative form has a checkbox to "create a patient from the
                # relative"
                for form in patient_relative_formset:
                    if form.tag == tag:  # must be a better way to do this ...
                        if form.create_patient_flag:
                            patient_relative_model.create_patient_from_myself(
                                registry_model,
                                patient_model.working_groups.all())
