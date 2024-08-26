import logging
from enum import Enum

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic.base import View

from rdrf.helpers.utils import consent_check, is_authorised

logger = logging.getLogger(__name__)


class FormTypes(Enum):
    DEMOGRAPHICS = "Demographics"
    CONSENTS = "Consents"
    REGISTRY = "Registry"


class Action:
    def __init__(self, request):
        self.request = request
        self.command = self._parse_command()
        self.user = self.request.user

    def run(self):
        if self.command == "form":
            return self._process_form()
        else:
            raise Http404

    def _parse_command(self):
        return self.request.GET.get("action")

    def _get_field(self, field):
        value = self.request.GET.get(field)
        return value

    def _get_patient(self):
        from registry.patients.models import ParentGuardian, Patient

        if "id" in self.request.GET:
            patient_id = self.request.GET.get("id")
            try:
                patient_model = Patient.objects.get(id=patient_id)
                if not is_authorised(self.user, patient_model):
                    logger.warning(
                        f"action not authorised for user:{self.user.id} on patient:{patient_model}"
                    )
                    raise PermissionError
                else:
                    return patient_model

            except Patient.DoesNotExist:
                raise Http404(_("Patient not found"))

        try:
            patient_model = (
                Patient.objects.filter(user=self.user).order_by("id").first()
            )
            if patient_model is not None:
                return patient_model
        except Patient.DoesNotExist:
            pass

        try:
            parent = ParentGuardian.objects.get(user=self.user)
            # what to do if there is more than one child
            # for now we take the first
            children = parent.children
            if children:
                return children[0]
        except ParentGuardian.DoesNotExist:
            pass

        raise Http404(_("No patients found. Please create a patient"))

    def _process_form(self):
        from rdrf.models.definition.models import Registry

        registry_code = self._get_field("registry")
        registry_model = get_object_or_404(Registry, code=registry_code)

        if not self.user.in_registry(registry_model):
            raise PermissionDenied

        form_type = self._get_field("form_type")

        patient_model = self._get_patient()

        if not patient_model.in_registry(registry_model.code):
            raise PermissionDenied

        if form_type == FormTypes.CONSENTS.value:
            return self._redirect_consents_form(registry_model, patient_model)

        if not consent_check(
            registry_model, self.user, patient_model, "see_patient"
        ):
            messages.error(
                self.request, "Patient consent required before continuing"
            )
            return self._redirect_consents_form(registry_model, patient_model)

        if form_type == FormTypes.DEMOGRAPHICS.value:
            return self._redirect_demographics_form(
                registry_model, patient_model
            )
        elif form_type == FormTypes.REGISTRY.value:
            return self._redirect_registry_form(registry_model, patient_model)
        else:
            raise Http404

    @staticmethod
    def _redirect_demographics_form(registry_model, patient_model):
        from django.urls import reverse

        return HttpResponseRedirect(
            reverse(
                "patient_edit",
                kwargs={
                    "registry_code": registry_model.code,
                    "patient_id": patient_model.id,
                },
            )
        )

    @staticmethod
    def _redirect_consents_form(registry_model, patient_model):
        from django.urls import reverse

        return HttpResponseRedirect(
            reverse(
                "consent_form_view",
                kwargs={
                    "registry_code": registry_model.code,
                    "patient_id": patient_model.id,
                },
            )
        )

    def _redirect_registry_form(self, registry_model, patient_model):
        from django.urls import reverse

        from rdrf.models.definition.models import (
            ContextFormGroup,
            RDRFContext,
            RegistryForm,
        )

        form_name = self._get_field("form")
        form_model = get_object_or_404(
            RegistryForm, name=form_name, registry=registry_model
        )

        cfg_name = self._get_field("cfg")
        cfg_model = get_object_or_404(
            ContextFormGroup, name=cfg_name, registry=registry_model
        )

        if cfg_model.is_fixed:
            context_model = get_object_or_404(
                RDRFContext.objects.get_for_patient(
                    patient_model, registry_model
                ),
                context_form_group=cfg_model,
            )

            return HttpResponseRedirect(
                reverse(
                    "registry_form",
                    kwargs={
                        "registry_code": registry_model.code,
                        "form_id": form_model.pk,
                        "patient_id": patient_model.pk,
                        "context_id": context_model.pk,
                    },
                )
            )
        elif cfg_model.is_multiple:
            return HttpResponseRedirect(
                reverse(
                    "form_add",
                    kwargs={
                        "registry_code": registry_model.code,
                        "form_id": form_model.pk,
                        "patient_id": patient_model.pk,
                        "context_id": "add",
                    },
                )
            )
        else:
            raise Http404


class ActionExecutorView(View):
    def get(self, request):
        action = Action(request)
        return action.run()
