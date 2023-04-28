import logging

from django.contrib import messages
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View

from rdrf.users.forms import EmailChangeForm
from rdrf.users.utils import sync_user_email_update

logger = logging.getLogger(__name__)


class ChangeEmailAddressView(View):

    @staticmethod
    def _render_template(request, user, form):

        context = {
            'current_username': user.username,
            'current_email': user.email,
            'patient': user.patient,
            'form': form
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
            sync_user_email_update(user, form.cleaned_data['new_email'])
            messages.add_message(self.request,
                                 messages.SUCCESS,
                                 f'{_("Email address has been updated successfully for user")}: {user.get_full_name()}')
            return redirect('email_address_change')
        else:
            form.add_error(NON_FIELD_ERRORS, ValidationError(f'{_("Email address has failed for user")}: {user.get_full_name()}'))

        return self._render_template(request, user, form)
