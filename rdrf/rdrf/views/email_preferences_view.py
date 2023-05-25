import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View

from rdrf.forms.email_preferences import EmailPreferencesForm
from rdrf.models.definition.models import EmailPreference
from rdrf.security.mixins import TokenAuthenticatedMixin
from registry.groups.models import CustomUser

logger = logging.getLogger(__name__)


MAX_TOKEN_AGE = 60 * 60 * 24 * 30


class UnsubscribeAllView(TokenAuthenticatedMixin, View):

    max_age = MAX_TOKEN_AGE

    def get(self, request, *args, **kwargs):

        email_preference, created = EmailPreference.objects.update_or_create(user=self.user,
                                                                             defaults={'unsubscribe_all': True})
        unsubscribe_successful = email_preference is not None

        if not unsubscribe_successful:
            raise Exception('Unsubscribe all failed for user', (self.user.username, self.is_valid_token))

        return render(request, 'email_preference/unsubscribe_all_success.html', {})


class EmailPreferencesView(TokenAuthenticatedMixin, View):

    max_age = MAX_TOKEN_AGE

    def get(self, request, *args, **kwargs):
        form = EmailPreferencesForm(self.user)

        context = {
            'state': request.GET.get('state'),
            'form': form,
            'instance': form.instance
        }
        return render(request, 'email_preference/email_preferences.html', context)

    def post(self, request, *args, **kwargs):
        success = False
        form = EmailPreferencesForm(self.user, request.POST)

        if form.is_valid():
            form.save()
            success = True

        query = {
            'state': 'success' if success else 'error'
        }

        redirect_kwargs = {'username_b64': self.username_b64,
                           'token': self.token}

        return redirect(reverse('email_preferences', kwargs=redirect_kwargs) + '?' + urlencode(query))
