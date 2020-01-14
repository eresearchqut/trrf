from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseNotFound
from django.views.generic.base import View

from rdrf.models.definition.models import Registry

from .mixins import LoginRequiredMixin


class PatientView(View, LoginRequiredMixin):

    def get(self, request, registry_code):
        registry = get_object_or_404(Registry, code=registry_code)
        if request.user.is_carer:
            patient = request.user.patients_in_care.filter(rdrf_registry=registry).first()
        else:
            patient = request.user.user_object.first()
        if patient is None:
            return HttpResponseNotFound()
        return redirect(reverse("patient_edit", args=[registry_code, patient.id]))
