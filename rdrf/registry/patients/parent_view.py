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
from rdrf.forms.progress import form_progress
from rdrf.helpers.utils import consent_status_for_patient
from rdrf.models.definition.models import Registry, RegistryForm

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
        progress = form_progress.FormProgress(self.registry)
        fth = FormTitleHelper(self.registry, "")

        context = {
            "parent": self.parent,
            "patients": [{
                "patient": patient,
                "consent": consent_status_for_patient(registry_code, patient),
                "form_groups": [{
                    "name": group_title,
                    "forms": [{
                        "form": form,
                        "progress": progress.get_form_progress(form, patient),
                        "current": progress.get_form_currency(form, patient),
                        "readonly": request.user.has_perm("rdrf.form_%s_is_readonly" % form.id),
                        "url": self._get_form_url(patient, form, cfg)
                    } for form in forms]
                } for cfg, group_title, forms in self._get_form_groups(patient)]
            } for patient in self._get_parent_patients(self.parent)],
            "registry_code": registry_code,
            "form_titles": fth.all_titles_for_user(request.user)
        }

        return render(request, 'rdrf_cdes/parent.html', context)

    def _get_parent_patients(self, parent):
        for patient in parent.patient.all():
            self.rdrf_context_manager.get_or_create_default_context(patient)
            yield patient

    def _get_form_url(self, patient, form, context_form_group=None):
        if context_form_group:
            if context_form_group.is_fixed:
                assert len(context_form_group.patient_contexts) > 0, f"Patient missing context for {context_form_group}"
                context_id = context_form_group.patient_contexts[0].pk
                return reverse("registry_form", args=[self.registry.code, form.id, patient.id, context_id])
            elif context_form_group.is_multiple:
                return reverse("form_add", args=[self.registry.code, form.id, patient.id, "add"])
        else:
            context_id = self.rdrf_context_manager.get_or_create_default_context(patient).pk
            return reverse("registry_form", args=[self.registry.code, form.id, patient.id, context_id])

    def _get_form_groups(self, patient):
        if self.rdrf_context_manager.supports_contexts:
            for context_form_group in self.rdrf_context_manager.get_patient_current_contexts(patient):
                yield context_form_group, context_form_group.name, context_form_group.forms
        else:
            forms = RegistryForm.objects.filter(registry=self.registry)\
                .exclude(is_questionnaire=True)\
                .order_by('position')
            yield None, "Modules", forms

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
