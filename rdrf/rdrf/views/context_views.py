import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic.base import View
from registry.patients.models import Patient

from rdrf.forms.components import RDRFContextLauncherComponent
from rdrf.forms.navigation.locators import PatientLocator
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.helpers.utils import get_error_messages, get_form_links
from rdrf.models.definition.models import (
    ContextFormGroup,
    RDRFContext,
    Registry,
)

logger = logging.getLogger("registry_log")


class ContextForm(ModelForm):
    class Meta:
        model = RDRFContext
        fields = ["display_name"]


class ContextFormGroupHelperMixin(object):
    def get_context_form_group(self, form_group_id):
        if form_group_id is None:
            return None
        return ContextFormGroup.objects.get(pk=form_group_id)

    def get_context_name(self, registry_model, context_form_group):
        if not registry_model.has_feature(RegistryFeatures.CONTEXTS):
            raise Exception("Registry does not support contexts")
        if context_form_group is None:
            return registry_model.metadata.get("context_name", "Context")
        return context_form_group.name

    def get_context_launcher(
        self, user, registry_model, patient_model, context_model=None
    ):
        context_launcher = RDRFContextLauncherComponent(
            user, registry_model, patient_model, "", context_model
        )

        return context_launcher.html

    def get_naming_info(self, form_group_id):
        if form_group_id is None:
            return "Display Name will default to 'Modules' if left blank"
        context_form_group = ContextFormGroup.objects.get(id=form_group_id)
        return context_form_group.naming_info

    def get_default_name(self, patient_model, context_form_group_model):
        if context_form_group_model is None:
            return "Modules"
        return context_form_group_model.get_default_name(patient_model)

    def allowed(self, user, registry_code, patient_id, context_id=None):
        try:
            registry_model = Registry.objects.get(code=registry_code)
            if not registry_model.has_feature(RegistryFeatures.CONTEXTS):
                return False
            patient_model = Patient.objects.get(pk=patient_id)
            patient_working_groups = set(patient_model.working_groups.all())
            context_model = (
                RDRFContext.objects.get(pk=context_id) if context_id else None
            )
            user_working_groups = set(
                registry_model.workinggroup_set.all()
                if user.is_superuser
                else user.working_groups.all()
            )

            if not user.is_superuser and not user.in_registry(registry_model):
                return False
            if (
                context_model
                and context_model.registry.code != registry_model.code
            ):
                return False
            if not (patient_working_groups <= user_working_groups):
                return False
            return True
        except Exception:
            logger.exception("error in context allowed check")
            return False

    def create_context_and_goto_form(
        self, registry_model, patient_model, context_form_group
    ):
        assert (
            len(context_form_group.forms) == 1
        ), "Direct link only possible if num forms in form group is 1"
        patient_content_type = ContentType.objects.get_for_model(patient_model)
        form_model = context_form_group.forms[0]
        context_model = RDRFContext()
        context_model.registry = registry_model
        context_model.name = "change me"
        context_model.content_object = patient_model
        context_model.content_type = patient_content_type
        context_model.context_form_group = context_form_group

        context_model.save()
        form_link = reverse(
            "registry_form",
            args=(
                registry_model.code,
                form_model.id,
                patient_model.pk,
                context_model.id,
            ),
        )

        return HttpResponseRedirect(form_link)


class RDRFContextCreateView(View, ContextFormGroupHelperMixin):
    model = RDRFContext

    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy("contextslisting")

    def get(
        self, request, registry_code, patient_id, context_form_group_id=None
    ):
        if not self.allowed(request.user, registry_code, patient_id):
            raise PermissionDenied

        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)
        context_form_group = self.get_context_form_group(context_form_group_id)
        naming_info = self.get_naming_info(context_form_group_id)

        context_name = self.get_context_name(registry_model, context_form_group)
        default_display_name = self.get_default_name(
            patient_model, context_form_group
        )
        default_values = {"display_name": default_display_name}

        if context_form_group and context_form_group.supports_direct_linking:
            return self.create_context_and_goto_form(
                registry_model, patient_model, context_form_group
            )

        context = {
            "location": "Add %s" % context_name,
            "registry": registry_model.code,
            "patient_id": patient_id,
            "form_links": [],
            "context_name": context_name,
            "patient_link": PatientLocator(registry_model, patient_model).link,
            "patient_name": patient_model.display_name,
            "context_launcher": self.get_context_launcher(
                request.user, registry_model, patient_model
            ),
            "naming_info": naming_info,
            "form": ContextForm(initial=default_values),
        }

        return render(request, "rdrf_cdes/rdrf_context.html", context)

    def post(
        self, request, registry_code, patient_id, context_form_group_id=None
    ):
        if not self.allowed(request.user, registry_code, patient_id):
            raise PermissionDenied

        form = ContextForm(request.POST)
        registry_model = Registry.objects.get(code=registry_code)
        patient_model = Patient.objects.get(pk=patient_id)

        context_form_group_model = self.get_context_form_group(
            context_form_group_id
        )
        naming_info = self.get_naming_info(context_form_group_id)
        context_name = self.get_context_name(
            registry_model, context_form_group_model
        )

        if form.is_valid():
            patient_model = Patient.objects.get(id=patient_id)
            registry_model = Registry.objects.get(code=registry_code)
            content_type = ContentType.objects.get_for_model(patient_model)
            context_model = form.save(commit=False)
            context_model.registry = registry_model
            context_model.content_type = content_type
            context_model.content_object = patient_model
            if context_form_group_model:
                context_model.context_form_group = context_form_group_model

            context_model.save()
            context_edit = reverse(
                "context_edit",
                kwargs={
                    "registry_code": registry_model.code,
                    "patient_id": patient_model.pk,
                    "context_id": context_model.pk,
                },
            )

            return HttpResponseRedirect(context_edit)
        else:
            error_messages = get_error_messages([form])
            context = {
                "location": "Add %s" % context_name,
                "errors": True,
                "error_messages": error_messages,
                "registry": registry_model.code,
                "patient_link": PatientLocator(
                    registry_model, patient_model
                ).link,
                "patient_id": patient_id,
                "form_links": [],
                "naming_info": naming_info,
                "context_launcher": self.get_context_launcher(
                    request.user, registry_model, patient_model
                ),
                "patient_name": patient_model.display_name,
                "form": ContextForm(request.POST),
            }

        return render(request, "rdrf_cdes/rdrf_context.html", context)


class RDRFContextEditView(View, ContextFormGroupHelperMixin):
    model = RDRFContext
    template_name = "rdrf_cdes/rdrf_context.html"
    success_url = reverse_lazy("contextslisting")

    def get(self, request, registry_code, patient_id, context_id):
        rdrf_context_model = get_object_or_404(RDRFContext, pk=context_id)

        if not self.allowed(
            request.user, registry_code, patient_id, context_id
        ):
            raise PermissionDenied

        context_form = ContextForm(instance=rdrf_context_model)

        patient_model = rdrf_context_model.content_object
        registry_model = rdrf_context_model.registry
        patient_name = patient_model.display_name
        if rdrf_context_model.context_form_group:
            context_form_group_model = self.get_context_form_group(
                rdrf_context_model.context_form_group.pk
            )
            naming_info = context_form_group_model.naming_info
        else:
            context_form_group_model = None
            naming_info = self.get_naming_info(None)

        context_name = self.get_context_name(
            registry_model, context_form_group_model
        )

        form_links = get_form_links(
            request.user,
            rdrf_context_model.object_id,
            rdrf_context_model.registry,
            rdrf_context_model,
        )

        context = {
            "location": "Edit %s" % context_name,
            "context_id": context_id,
            "patient_name": patient_name,
            "form_links": form_links,
            "patient_link": PatientLocator(registry_model, patient_model).link,
            "context_launcher": self.get_context_launcher(
                request.user, registry_model, patient_model
            ),
            "context_name": context_name,
            "registry": registry_model.code,
            "naming_info": naming_info,
            "patient_id": patient_id,
            "form": context_form,
        }

        return render(request, "rdrf_cdes/rdrf_context.html", context)

    def post(self, request, registry_code, patient_id, context_id):
        registry_model = Registry.objects.get(code=registry_code)
        context_model = RDRFContext.objects.get(pk=context_id)
        context_form_group_model = context_model.context_form_group
        if context_form_group_model:
            naming_info = context_form_group_model.naming_info
        else:
            naming_info = self.get_naming_info(None)
        context_name = context_model.registry.metadata.get(
            "context_name", "Context"
        )
        patient_model = Patient.objects.get(id=patient_id)
        form = ContextForm(request.POST, instance=context_model)

        if form.is_valid():
            content_type = ContentType.objects.get_for_model(patient_model)
            context_model = form.save(commit=False)
            context_model.registry = registry_model
            context_model.content_type = content_type
            context_model.content_object = patient_model
            context_model.save()
            form_links = get_form_links(
                request.user,
                context_model.object_id,
                context_model.registry,
                context_model,
            )

            context = {
                "location": "Edit %s" % context_name,
                "patient_name": patient_model.display_name,
                "patient_link": PatientLocator(
                    registry_model, patient_model
                ).link,
                "form_links": form_links,
                "context_launcher": self.get_context_launcher(
                    request.user, registry_model, patient_model
                ),
                "message": "%s saved successfully" % context_name,
                "error_messages": [],
                "registry": registry_model.code,
                "naming_info": naming_info,
                "patient_id": patient_id,
                "form": ContextForm(instance=context_model),
            }

        else:
            error_messages = get_error_messages([form])

            context = {
                "location": "Add %s" % context_name,
                "errors": True,
                "error_messages": error_messages,
                "registry": registry_model.code,
                "patient_id": patient_id,
                "form_links": [],
                "patient_link": PatientLocator(
                    registry_model, patient_model
                ).link,
                "context_launcher": self.get_context_launcher(
                    request.user, registry_model, patient_model
                ),
                "naming_info": naming_info,
                "patient_name": patient_model.display_name,
                "form": ContextForm(request.POST),
            }

        return render(request, "rdrf_cdes/rdrf_context.html", context)
