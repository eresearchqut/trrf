import logging
import datetime

from django.contrib import messages, auth
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from rdrf.security.mixins import TokenAuthenticatedMixin
from rdrf.users.forms import EmailChangeForm
from rdrf.users.utils import create_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS, \
    activate_email_change_request, EMAIL_CHANGE_REQUEST_EXPIRY_HOURS
from registry.groups.models import EmailChangeRequest, EmailChangeRequestStatus

logger = logging.getLogger(__name__)


class EmailChangeRequestView(View):

    @staticmethod
    def _render_template(request, user, form):
        # An existing email change request is only considered current if it was requested within the last 2 weeks
        last_2_weeks = datetime.datetime.now() + datetime.timedelta(weeks=-2)
        current_request = EmailChangeRequest.objects.filter(user=user, request_date__gte=last_2_weeks).first()

        # Has the activation link most likely expired?
        activation_expiry_hours = datetime.datetime.now() + datetime.timedelta(hours=-EMAIL_CHANGE_REQUEST_EXPIRY_HOURS)
        is_expired = current_request and not current_request.request_date >= activation_expiry_hours

        context = {
            'current_username': user.username,
            'current_email': user.email,
            'patient': user.patient,
            'form': form,
            'current_request': current_request,
            'is_expired': is_expired,
            'expiry_hours': EMAIL_CHANGE_REQUEST_EXPIRY_HOURS,
            'EmailChangeRequestStatus': EmailChangeRequestStatus
        }

        return render(request, 'user/change_email_address.html', context=context)

    def get(self, request):
        user = request.user
        form = EmailChangeForm(user=request.user)

        return self._render_template(request, user, form)

    def post(self, request):
        user = request.user
        form = EmailChangeForm(request.POST, user=user)

        if form.is_valid():
            create_email_change_request(user, form.cleaned_data['new_email'])
            messages.add_message(self.request,
                                 messages.SUCCESS,
                                 f'{_("An Email address change request has been created for user")}: {user.get_full_name()}')
            return redirect('email_address_change')
        else:
            form.add_error(NON_FIELD_ERRORS, ValidationError(f'{_("Email address has failed for user")}: {user.get_full_name()}'))

        return self._render_template(request, user, form)

    def delete(self, request):
        user = request.user
        user.emailchangerequest.delete()
        return HttpResponse(status=204)


class ActivateEmailChangeRequestView(TokenAuthenticatedMixin, View):
    max_age = EMAIL_CHANGE_REQUEST_EXPIRY_SECONDS

    def get(self, request, *args, **kwargs):
        activate_email_change_request(self.user)
        auth.logout(request)  # Force logout, requiring the user to reauthenticate with their new email address
        return redirect(reverse('registration_activation_complete'))
