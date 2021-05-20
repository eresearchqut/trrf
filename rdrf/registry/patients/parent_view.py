import logging

from django.core.exceptions import PermissionDenied
from django.views.generic.base import View
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages

from registry.patients.admin_forms import ParentGuardianForm
from registry.patients.models import AddressType, ParentGuardian, Patient, PatientAddress

from rdrf.db.contexts_api import RDRFContextManager
from rdrf.forms.form_title_helper import FormTitleHelper
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry

logger = logging.getLogger("registry_log")


class RDRFContextSwitchError(Exception):
    pass


class BaseParentView(View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = None
        self.rdrf_context_manager = None
        self.parent = None

    _ADDRESS_TYPE = "Postal"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        self.registry = get_object_or_404(Registry, code=kwargs['registry_code'])
        if not request.user.in_registry(self.registry):
            raise PermissionDenied
        user_allowed = user.is_superuser or user.is_staff or user.is_parent
        if not user_allowed:
            raise PermissionDenied
        if 'parent_id' not in kwargs:
            self.parent = get_object_or_404(ParentGuardian, user=user)
        else:
            passed_in_parent = get_object_or_404(ParentGuardian, pk=kwargs['parent_id'])
            self.parent = ParentGuardian.objects.filter(user=user).first()
            if not self.parent and user.is_parent:
                raise PermissionDenied
            if self.parent.id != passed_in_parent.id:
                return PermissionDenied
            self.parent = passed_in_parent

        return super().dispatch(request, *args, **kwargs)


class ParentView(BaseParentView):

    def get(self, request, registry_code):
        self.rdrf_context_manager = RDRFContextManager(self.registry)
        fth = FormTitleHelper(self.registry, "")

        context = {
            "parent": self.parent,
            "patients": [{
                "patient": patient,
                "consent": consent_status_for_patient(registry_code, patient)
            } for patient in self._get_parent_patients(self.parent)],
            "registry_code": registry_code,
            "form_titles": fth.all_titles_for_user(request.user)
        }

        return render(request, 'rdrf_cdes/parent.html', context)

    def _get_parent_patients(self, parent):
        for patient in parent.patient.all():
            self.rdrf_context_manager.get_or_create_default_context(patient)
            yield patient

    def post(self, request, registry_code):

        patient = Patient.objects.create(
            consent=True,
            family_name=request.POST["surname"],
            given_names=request.POST["first_name"],
            date_of_birth=request.POST["date_of_birth"],
            sex=request.POST["gender"],
            created_by=request.user
        )
        patient.rdrf_registry.add(self.registry)

        patient.save()

        use_parent_address = "use_parent_address" in request.POST

        address_type, created = AddressType.objects.get_or_create(type=self._ADDRESS_TYPE)

        PatientAddress.objects.create(
            patient=patient,
            address_type=address_type,
            address=self.parent.address if use_parent_address else request.POST["address"],
            suburb=self.parent.suburb if use_parent_address else request.POST["suburb"],
            state=self.parent.state if use_parent_address else request.POST["state"],
            postcode=self.parent.postcode if use_parent_address else request.POST["postcode"],
            country=self.parent.country if use_parent_address else request.POST["country"]
        )

        self.parent.patient.add(patient)
        self.parent.save()

        # ParentGuardian doesn't have working group?
        # Hence we assign the working group of a newly created
        # patient based on the working group of the first registered patient
        registered_patient_working_group = None
        for p in self.parent.patient.all():
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
        context['parent'] = self.parent
        context['registry_code'] = registry_code
        context['parent_form'] = ParentGuardianForm(instance=self.parent)

        return render(request, "rdrf_cdes/parent_edit.html", context)

    def post(self, request, registry_code, parent_id):
        context = {}
        parent_form = ParentGuardianForm(request.POST, instance=self.parent)
        if parent_form.is_valid():
            parent_form.save()
            self.update_name(request.user, parent_form.cleaned_data)
            messages.add_message(request, messages.SUCCESS, "Details saved")
        else:
            messages.add_message(request, messages.ERROR, "Please correct the errors bellow")

        registry = Registry.objects.get(code=registry_code)

        context['parent'] = self.parent
        context['registry_code'] = registry_code
        context['parent_form'] = parent_form
        fth = FormTitleHelper(registry, "")
        context['form_titles'] = fth.all_titles_for_user(request.user)

        return render(request, "rdrf_cdes/parent_edit.html", context)
