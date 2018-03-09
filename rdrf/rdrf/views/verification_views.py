from django.views.generic.base import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from rdrf.models.definition.models import Registry
from rdrf.workflows.verification import get_verifiable_cdes
from rdrf.workflows.verification import verifications_needed
from rdrf.forms.dynamic.verification_form import make_verification_form
from registry.patients.models import Patient

class VerificationSecurityMixin:
    def security_check(self, user, registry_model):
        if not registry_model.has_feature("verification"):
            raise PermissionDenied()
        
        if not user.in_registry(registry_model):
            raise PermissionDenied()

        if not user.is_clinician:
            raise PermissionDenied()

        if not registry_model.has_feature("clinicians_have_patients"):
            raise PermissionDenied()
        
class PatientVerification:
    def __init__(self, registry_model, patient_model, verifications):
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.verifications = verifications

    @property
    def title(self):
        return "%s" % self.patient_model

    @property
    def number(self):
        return len(self.verifications)

    @property
    def link(self):
        return reverse("patient_verification", args=[self.registry_model.code,
                                                     self.patient_model.pk])

class PatientsRequiringVerificationView(View, VerificationSecurityMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
      
        patient_verifications =  []

        for patient_model in Patient.objects.filter(clinician=user):
                 verifications = verifications_needed(user, registry_model, patient_model)
                 if len(verifications) > 0:
                     patient_verifications.append(PatientVerification(registry_model, patient_model,verifications))
                 
        context = {
            "location": "Clinician Verification",
            "patient_verifications": patient_verifications,
        }
        
        return render(request, 'rdrf_cdes/patients_requiring_verifications.html', context)

        
class PatientVerificationView(View, VerificationSecurityMixin):
    @method_decorator(login_required)
    def get(self, request, registry_code, patient_id):
        user = request.user
        registry_model = Registry.objects.get(code=registry_code)
        self.security_check(user, registry_model)
        patient_model = Patient.objects.get(id=patient_id)

        verifications = verifications_needed(user,
                                        registry_model,
                                        patient_model)

        verification_form = make_verification_form(verifications)

        for field in verification_form:
            form_name, section_code, cde_code = field.name.split("____")
            for v in verifications:
                if all([v.form_model.name == form_name,
                        v.section_model.code == section_code,
                        v.cde_model.code == cde_code]):
                    field.patient_answer = v.get_data(patient_model)
                    
        context = {"form": verification_form,
                   "patient": patient_model}

        return render(request, 'rdrf_cdes/patient_verification.html', context)

    @method_decorator(login_required)
    def post(self, request, registry_code, patient_id):
        form = generate_verifcation_form(request, registry_code, patient_id)
        if form.is_valid():
            self._create_annotations(form)
        else:
            pass
    
