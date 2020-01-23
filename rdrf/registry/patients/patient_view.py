from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic.base import View

from rdrf.models.definition.models import Registry
from .mixins import LoginRequiredMixin


class PatientView(View, LoginRequiredMixin):

    def get(self, request, registry_code):
        _ = get_object_or_404(Registry, code=registry_code)
        patient = request.user.user_object.first()
        return redirect(reverse("patient_edit", args=[registry_code, patient.id, ]))
