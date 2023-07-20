import datetime
import logging

from django.contrib import messages, auth
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from rdrf.security.mixins import TokenAuthenticatedMixin, StaffMemberRequiredMixin
from rdrf.users.forms import EmailChangeForm
from rdrf.users.utils import initiate_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS, \
    activate_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_HOURS
from registry.groups.models import EmailChangeRequest, EmailChangeRequestStatus, CustomUser
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class BaseEmailChangeRequest(View):
    user = None

    def _redirect_response(self):
        return redirect('email_address_change')

    def _render_template(self, request, user, form):
        # An existing email change request is only considered current if it was requested within the last 2 weeks
        last_2_weeks = datetime.datetime.now() + datetime.timedelta(weeks=-2)
        current_request = EmailChangeRequest.objects.filter(user=user, request_date__gte=last_2_weeks).first()

        # Has the activation link most likely expired?
        activation_expiry_hours = datetime.datetime.now() + datetime.timedelta(hours=-EMAIL_CHANGE_REQUEST_EXPIRY_HOURS)
        is_expired = current_request and not current_request.request_date >= activation_expiry_hours

        context = {
            'form': form,
            'current_request': current_request,
            'is_expired': is_expired,
            'expiry_hours': EMAIL_CHANGE_REQUEST_EXPIRY_HOURS,
            'EmailChangeRequestStatus': EmailChangeRequestStatus
        }

        return render(request, 'user/change_email_address.html', context=context)

    def get(self, request, *args, **kwargs):
        form = EmailChangeForm(user=self.user, current_user=request.user)

        return self._render_template(request, self.user, form)

    def post(self, request, *args, **kwargs):
        form = EmailChangeForm(request.POST, user=self.user, current_user=request.user)

        if form.is_valid():
            requires_activation = form.cleaned_data['user_activation_required']
            initiate_email_change_request(self.user, form.cleaned_data['new_email'], requires_activation=requires_activation)
            messages.add_message(request,
                                 messages.SUCCESS,
                                 f'{_("An Email address change request has been created for user")}: {self.user.get_full_name()}')

            return self._redirect_response()
        else:
            form.add_error(NON_FIELD_ERRORS,
                           ValidationError(
                               f'{_("Email address change request has failed for user")}: {self.user.get_full_name()}'))

        return self._render_template(request, self.user, form)

    def delete(self, request, *args, **kwargs):
        self.user.emailchangerequest.delete()
        return HttpResponse(status=204)


def get_user_by_user(user, request_user):
    def _get_common_patient_registry(patient):
        patient_registry = patient.rdrf_registry.first()
        if patient_registry in request_user.registry.all():
            return patient_registry

    if request_user.is_superuser:
        return user  # Superuser has automatic access to this user

    if request_user.is_staff:
        # Filter the users by those that the current logged in staff member has access to
        users = CustomUser.objects.get_by_user(request_user)
    elif user.is_patient:
        # Filter the patients by those the current user has access to
        common_registry = _get_common_patient_registry(user.patient)
        users = Patient.objects.get_by_user_and_registry(request_user, common_registry).values('user').annotate(id=F('user'))
    else:
        raise PermissionDenied()

    # Select the user from the filtered list.
    # Failure to find the user in the list indicates the request_user does not have access
    try:
        return users.get(id=user.id)
    except ObjectDoesNotExist:
        raise PermissionDenied()


class SelfEmailChangeRequestView(BaseEmailChangeRequest):

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super().dispatch(request, *args, **kwargs)

    def _redirect_response(self):
        return redirect('email_address_change')


class PatientEmailChangeRequestView(PermissionRequiredMixin, BaseEmailChangeRequest):
    permission_required = ('patients.change_patientuser',)

    def dispatch(self, request, *args, **kwargs):
        patient_id = kwargs.pop('patient_id')
        patient = get_object_or_404(Patient, id=patient_id)
        self.user = get_user_by_user(patient.user, request.user)
        return super().dispatch(request, *args, **kwargs)

    def _redirect_response(self):
        return redirect(reverse('patient_email_change', kwargs={'patient_id': self.user.patient.id}))


class UserAdminEmailChangeRequestView(PermissionRequiredMixin, StaffMemberRequiredMixin, BaseEmailChangeRequest):
    permission_required = ('groups.change_customuser',)

    def dispatch(self, request, *args, **kwargs):
        user_id = kwargs.pop('user_id')
        self.user = get_user_by_user(get_object_or_404(CustomUser, id=user_id), request.user)
        return super().dispatch(request, *args, **kwargs)

    def _redirect_response(self):
        return redirect(reverse('user_email_change', kwargs={'user_id': self.user.id}))


class ActivateEmailChangeRequestView(TokenAuthenticatedMixin, View):
    max_age = EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS

    def get(self, request, *args, **kwargs):
        pending_request = EmailChangeRequest.objects.filter(user=self.user, status=EmailChangeRequestStatus.PENDING).first()

        context = {'registry': self.user.my_registry,
                   'pending_request': pending_request}

        return render(request, 'user/activate_email_change_request.html', context)

    def post(self, request, *args, **kwargs):
        activate_email_change_request(self.user)
        if request.user == self.user:
            auth.logout(request)  # Force logout, requiring the user to reauthenticate with their new email address
        return redirect(reverse('registration_activation_complete'))
