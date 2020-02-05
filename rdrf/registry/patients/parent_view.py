import logging

from django.views.generic.base import View
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model

from registry.groups.models import WorkingGroup
from registry.patients.admin_forms import ParentGuardianForm
from registry.patients.models import AddressType, ParentGuardian, Patient, PatientAddress

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.forms.form_title_helper import FormTitleHelper
from rdrf.forms.progress import form_progress
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry, RegistryForm

from .mixins import LoginRequiredMixin

logger = logging.getLogger("registry_log")


class RDRFContextSwitchError(Exception):
    pass


class BaseParentView(View, LoginRequiredMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = None
        self.rdrf_context_manager = None

    _OTHER_CLINICIAN = "clinician-other"
    _UNALLOCATED_GROUP = "Unallocated"

    _ADDRESS_TYPE = "Postal"

    def get_clinician_centre(self, request, registry):

        working_group = None

        try:
            clinician_id, working_group_id = request.POST['clinician'].split("_")
            clinician = get_user_model().objects.get(id=clinician_id)
            working_group = WorkingGroup.objects.get(id=working_group_id)
        except ValueError:
            clinician = None
            working_group, status = WorkingGroup.objects.get_or_create(
                name=self._UNALLOCATED_GROUP, registry=registry)

        return clinician, working_group


class ParentView(BaseParentView):

    def get(self, request, registry_code):
        context = {}
        if request.user.is_authenticated:
            parent = ParentGuardian.objects.get(user=request.user)
            registry = Registry.objects.get(code=registry_code)

            self.registry = registry
            self.rdrf_context_manager = RDRFContextManager(self.registry)

            patients_objects = parent.patient.all()
            patients = []

            forms_objects = RegistryForm.objects.filter(registry=registry).exclude(is_questionnaire=True).order_by('position')

            progress = form_progress.FormProgress(registry)

            for patient in patients_objects:
                forms = []
                for form in forms_objects:
                    if form.is_questionnaire or not request.user.can_view(form):
                        continue
                    forms.append({
                        "form": form,
                        "progress": progress.get_form_progress(form, patient),
                        "current": progress.get_form_currency(form, patient),
                        "readonly": request.user.has_perm("rdrf.form_%s_is_readonly" % form.id)
                    })

                rdrf_context = self.rdrf_context_manager.get_or_create_default_context(patient)
                patients.append({
                    "patient": patient,
                    "consent": consent_status_for_patient(registry_code, patient),
                    "context_id": rdrf_context.pk,
                    "forms": forms
                })

            context['parent'] = parent
            context['patients'] = patients
            context['registry_code'] = registry_code

            fth = FormTitleHelper(self.registry, "")
            context['form_titles'] = fth.all_titles_for_user(request.user)

        return render(request, 'rdrf_cdes/parent.html', context)

    def post(self, request, registry_code):
        parent = ParentGuardian.objects.get(user=request.user)
        registry = Registry.objects.get(code=registry_code)

        patient = Patient.objects.create(
            consent=True,
            family_name=request.POST["surname"],
            given_names=request.POST["first_name"],
            date_of_birth=request.POST["date_of_birth"],
            sex=request.POST["gender"],
            created_by=request.user
        )
        patient.rdrf_registry.add(registry)

        patient.save()

        use_parent_address = "use_parent_address" in request.POST

        address_type, created = AddressType.objects.get_or_create(type=self._ADDRESS_TYPE)

        PatientAddress.objects.create(
            patient=patient,
            address_type=address_type,
            address=parent.address if use_parent_address else request.POST["address"],
            suburb=parent.suburb if use_parent_address else request.POST["suburb"],
            state=parent.state if use_parent_address else request.POST["state"],
            postcode=parent.postcode if use_parent_address else request.POST["postcode"],
            country=parent.country if use_parent_address else request.POST["country"]
        )

        parent.patient.add(patient)
        parent.save()

        # ParentGuardian doesn't have working group?
        # Hence we assign the working group of a newly created
        # patient based on the working group of the first registered patient
        registered_patient_working_group = None
        for p in parent.patient.all():
            wg = p.working_groups.first()
            if wg:
                registered_patient_working_group = wg
                break

        if registered_patient_working_group:
            patient.working_groups.add(registered_patient_working_group)
            patient.save()

        messages.add_message(request, messages.SUCCESS, 'Patient added successfully')
        return redirect(reverse("registry:parent_page", args={registry_code: registry_code}))


class ParentEditView(BaseParentView):

    def update_name(self, user, form):
        first_name = form['first_name']
        last_name = form['last_name']
        if user.first_name != first_name or user.last_name != last_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

    def get(self, request, registry_code, parent_id):
        context = {}
        parent = ParentGuardian.objects.get(user=request.user)

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = ParentGuardianForm(instance=parent)

        return render(request, "rdrf_cdes/parent_edit.html", context)

    def post(self, request, registry_code, parent_id):
        context = {}
        parent = ParentGuardian.objects.get(id=parent_id)

        parent_form = ParentGuardianForm(request.POST, instance=parent)
        if parent_form.is_valid():
            parent_form.save()
            self.update_name(request.user, parent_form.cleaned_data)
            messages.add_message(request, messages.SUCCESS, "Details saved")
        else:
            messages.add_message(request, messages.ERROR, "Please correct the errors bellow")

        registry = Registry.objects.get(code=registry_code)

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = parent_form
        fth = FormTitleHelper(registry, "")
        context['form_titles'] = fth.all_titles_for_user(request.user)

        return render(request, "rdrf_cdes/parent_edit.html", context)
