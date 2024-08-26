from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic.base import View

from rdrf.models.definition.models import Registry


class PatientView(View):
    def get(self, request, registry_code):
        registry = get_object_or_404(Registry, code=registry_code)
        user = request.user
        qs = (
            user.patients_in_care if request.user.is_carer else user.user_object
        )
        patient = get_object_or_404(qs, rdrf_registry=registry)
        return redirect(
            reverse("patient_edit", args=[registry_code, patient.id])
        )
