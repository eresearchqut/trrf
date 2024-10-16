import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import ChoiceField
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.template.context_processors import csrf
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import View
from registry.groups.models import CustomUser
from registry.patients.models import ClinicianOther, ParentGuardian, Patient

from rdrf.forms.components import (
    RDRFContextLauncherComponent,
    RDRFPatientInfoComponent,
)
from rdrf.forms.navigation.locators import PatientLocator
from rdrf.forms.navigation.wizard import NavigationFormType, NavigationWizard
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import Registry
from rdrf.models.workflow_models import ClinicianSignupRequest
from rdrf.security.security_checks import security_check_user_patient

logger = logging.getLogger(__name__)


class ClinicianForm(forms.ModelForm):
    EMPTY_CHOICE = -1
    OTHER_CHOICE = -2

    user = ChoiceField(label=_("Preferred Clinician"), choices=[])

    class Meta:
        model = ClinicianOther
        fields = [
            "user",
            "clinician_first_name",
            "clinician_last_name",
            "clinician_hospital",
            "clinician_address",
            "clinician_email",
            "clinician_phone_number",
            "patient",
            "speciality",
            "use_other",
        ]

        widgets = {
            "patient": forms.HiddenInput(),
            "use_other": forms.HiddenInput(),
        }

    def __init__(
        self, registry_model, initial=None, post_data=None, instance=None
    ):
        if initial is None:
            initial = {}
        self.registry_model = registry_model

        if post_data:
            if instance:
                super().__init__(post_data, instance=instance)
            else:
                super().__init__(post_data)

        else:
            if instance:
                super().__init__(instance=instance)
            else:
                super().__init__(initial=initial)

        self.fields["user"].choices = self._get_clinician_choices()
        self.fields["user"].css = "nohide"

    def _get_clinician_choices(self):
        empty_choice = [self.EMPTY_CHOICE, "---"]
        clinicians = [
            self._option_from_instance(clinician_user)
            for clinician_user in self._get_users_queryset(self.registry_model)
        ]

        clinicians.append([self.OTHER_CHOICE, _("Other - Not Listed")])
        clinicians.insert(0, empty_choice)
        return clinicians

    def clean(self):
        cleaned_data = super().clean()

        clinician_choice = int(cleaned_data["user"])
        del cleaned_data["user"]
        clinician_first_name = cleaned_data.get("clinician_first_name", None)
        clinician_last_name = cleaned_data.get("clinician_last_name", None)

        if clinician_choice == self.OTHER_CHOICE:
            if not all([clinician_first_name, clinician_last_name]):
                raise ValidationError(_("Please enter first and last name"))
            else:
                cleaned_data["user"] = None
                cleaned_data["use_other"] = True

        elif clinician_choice == self.EMPTY_CHOICE:
            raise ValidationError(
                _(
                    "Please select existing clinician user or choose Other and enter details"
                )
            )

        else:
            try:
                clinician_user = CustomUser.objects.get(pk=clinician_choice)
                cleaned_data["user"] = clinician_user
                cleaned_data["use_other"] = False
            except CustomUser.DoesNotExist:
                raise ValidationError(_("Selected user does not exist"))

        return cleaned_data

    def _get_users_queryset(self, registry_model):
        try:
            clinicians_group = Group.objects.get(name="Clinical Staff")
            return CustomUser.objects.filter(
                registry__in=[self.registry_model],
                groups__in=[clinicians_group],
            )
        except Group.DoesNotExist:
            return CustomUser.objects.none()

    def _option_from_instance(self, clinician_user):
        if clinician_user.working_groups.count() == 1:
            working_group_names = clinician_user.working_groups.first().name
        else:
            working_group_names = ",".join(
                [wg.name for wg in clinician_user.working_groups.all()]
            )

        option_string = "%s %s (%s)" % (
            clinician_user.first_name,
            clinician_user.last_name,
            working_group_names,
        )

        return [clinician_user.pk, option_string]


class ClinicianFormView(View):
    def _get_template(self):
        return "rdrf_cdes/clinician.html"

    def get(self, request, registry_code, patient_id):
        self._get_objects(request, registry_code, patient_id)

        context = self._build_context()

        return self._render_context(request, context)

    def _build_context(self):
        context = {
            "location": "Clinician",
            "patient_link": PatientLocator(
                self.registry_model, self.patient_model
            ).link,
            "previous_form_link": self.wizard.previous_link,
            "next_form_link": self.wizard.next_link,
            "form_name": _("Supervising Clinician"),
            "registry_code": self.registry_model.code,
            "patient_model": self.patient_model,
            "parent": self.parent,
            "form": self.clinician_form,
            "context_launcher": self.context_launcher.html,
            "patient_info": RDRFPatientInfoComponent(
                self.registry_model, self.patient_model, self.request.user
            ).html,
        }

        return context

    def _get_navigation_wizard(self):
        return NavigationWizard(
            self.request.user,
            self.registry_model,
            self.patient_model,
            NavigationFormType.CLINICIAN,
            None,
            None,
        )

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render(request, self._get_template(), context)

    def _get_objects(self, request, registry_code, patient_id):
        self.request = request
        self.user = request.user
        self.message = None
        if self.user.is_parent:
            self.parent = ParentGuardian.objects.get(user=self.user)
        else:
            self.parent = None
        self.patient_model = get_object_or_404(Patient, pk=patient_id)

        security_check_user_patient(self.user, self.patient_model)
        self.registry_model = get_object_or_404(Registry, code=registry_code)
        if not self.registry_model.has_feature(RegistryFeatures.CLINICIAN_FORM):
            raise Http404

        self.patient_name = "%s %s" % (
            self.patient_model.given_names,
            self.patient_model.family_name,
        )

        try:
            logger.debug(request.POST)
            self.clinician_other_model = ClinicianOther.objects.get(
                patient=self.patient_model
            )
        except ClinicianOther.DoesNotExist:
            self.clinician_other_model = None

        if request.method == "POST":
            if self.clinician_other_model is None:
                self.clinician_form = ClinicianForm(
                    self.registry_model, post_data=request.POST
                )

            else:
                self.clinician_form = ClinicianForm(
                    self.registry_model,
                    post_data=request.POST,
                    instance=self.clinician_other_model,
                )
        else:
            if self.clinician_other_model:
                self.clinician_form = ClinicianForm(
                    self.registry_model, instance=self.clinician_other_model
                )
            else:
                self.clinician_form = ClinicianForm(
                    self.registry_model, initial={"patient": patient_id}
                )

        self.context_launcher = RDRFContextLauncherComponent(
            self.user, self.registry_model, self.patient_model, "Clinician"
        )

        self.wizard = self._get_navigation_wizard()

    @transaction.atomic()
    def post(self, request, registry_code, patient_id):
        self._get_objects(request, registry_code, patient_id)

        if self.clinician_form.is_valid():
            other_clinician_model = self.clinician_form.save()
            if other_clinician_model.user:
                other_clinician_model.patient.registered_clinicians.set(
                    [other_clinician_model.user]
                )
                # hack to get allow the notification
                other_clinician_model.patient.clinician_flag = True
                other_clinician_model.patient.save()

            other_clinician_model.synchronise_working_group()
            self.clinician_form = ClinicianForm(
                self.registry_model, instance=other_clinician_model
            )
            success_message = _(
                "Patient %(patient_name)s saved successfully"
            ) % {"patient_name": self.patient_name}
            messages.add_message(
                self.request, messages.SUCCESS, success_message
            )
        else:
            self.clinician_form = ClinicianForm(
                self.registry_model, post_data=request.POST
            )
            failure_message = _(
                "Patient %(patient_name)s not saved due to validation errors"
            ) % {"patient_name": self.patient_name}
            messages.add_message(self.request, messages.ERROR, failure_message)

        context = self._build_context()
        return self._render_context(request, context)


class ClinicianActivationView(View):
    """
    Clinician who receives an activation link lands here to confirm and
    create a user for themselves
    """

    def get(self, request):
        token = request.GET.get("t", None)
        if not token:
            raise Http404()

        csr = get_object_or_404(ClinicianSignupRequest, token=token)

        # populate the view data from the ClinicianOther model which stores
        # what the parent thinks is the correct data ...
        if csr.state != "requested":
            raise Http404()

        template_data = self._build_context(csr)

        return self._render_context(request, template_data)

    def _build_context(self, clinician_signup_request):
        context = {}
        clin = clinician_signup_request.clinician_other
        context["first_name"] = clin.first_name
        context["last_name"] = clin.last_name

        return context

    def _render_context(self, request, context):
        context.update(csrf(request))
        return render(request, self._get_template(), context)

    def _get_template(self):
        return "rdrf_cdes/clinician_activation.html"
