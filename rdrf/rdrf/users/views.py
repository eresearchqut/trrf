import datetime
import logging

from django.contrib import messages, auth
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError, PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from rdrf.security.mixins import TokenAuthenticatedMixin
from rdrf.users.forms import EmailChangeForm
from rdrf.users.utils import initiate_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS, \
    activate_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_HOURS
from registry.groups.models import EmailChangeRequest, EmailChangeRequestStatus
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


def _render_template(request, user, form):
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


def _post_email_change_request(request, user, patient_id=None):
    form = EmailChangeForm(request.POST, user=user, current_user=request.user)

    if form.is_valid():
        requires_activation = form.cleaned_data['patient_activation_required']
        initiate_email_change_request(user, form.cleaned_data['new_email'], requires_activation=requires_activation)
        messages.add_message(request,
                             messages.SUCCESS,
                             f'{_("An Email address change request has been created for user")}: {user.get_full_name()}')

        if request.user == user:
            return redirect('email_address_change')
        else:
            return redirect(reverse('patient_email_change', kwargs={'patient_id': patient_id}))
    else:
        form.add_error(NON_FIELD_ERRORS,
                       ValidationError(f'{_("Email address change request has failed for user")}: {user.get_full_name()}'))

    return _render_template(request, user, form)


class EmailChangeRequestView(View):
    def get(self, request):
        user = request.user
        form = EmailChangeForm(user=request.user, current_user=request.user)

        return _render_template(request, user, form)

    def post(self, request):
        return _post_email_change_request(request, request.user)

    def delete(self, request):
        user = request.user
        user.emailchangerequest.delete()
        return HttpResponse(status=204)


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


class PatientUserEmailView(PermissionRequiredMixin, View):
    permission_required = ('patients.change_patientuser',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient_id = None
        self.patient_user = None
        self.patient_registry = None

    def dispatch(self, request, *args, **kwargs):
        self.patient_id = kwargs.get('patient_id')

        # Retrieve patient being updated
        self.patient_registry = get_object_or_404(Patient, id=self.patient_id).rdrf_registry.first()

        # Filter the patients by those the current user has access to
        user_patients = Patient.objects.get_by_user_and_registry(request.user, self.patient_registry)

        # Select the patient from the filtered list
        try:
            self.patient_user = user_patients.get(id=self.patient_id).user
        except ObjectDoesNotExist:
            # if the patient is not in the user's list, then they don't have access.
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = EmailChangeForm(user=self.patient_user, current_user=request.user)

        return _render_template(request, self.patient_user, form)

    def post(self, request, *args, **kwargs):
        return _post_email_change_request(request, self.patient_user, self.patient_id)

    def delete(self, request, *args, **kwargs):
        self.patient_user.emailchangerequest.delete()
        return HttpResponse(status=204)
