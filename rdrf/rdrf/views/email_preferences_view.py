import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View

from rdrf.auth.signed_url.util import check_token
from rdrf.forms.email_preferences import EmailPreferencesForm
from rdrf.models.definition.models import EmailPreference
from registry.groups.models import CustomUser

logger = logging.getLogger(__name__)


class TokenAuthenticatedView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.username_b64 = None
        self.token = None

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            self.user = request.user
        else:
            self.username_b64 = kwargs.get('username_b64')
            self.token = kwargs.get('token')

            is_valid_token, username = check_token(self.username_b64, self.token)
            self.user = get_object_or_404(CustomUser, username=username, is_active=True)

            if not is_valid_token:
                raise Exception('Invalid token')

        return super().dispatch(request, *args, **kwargs)


class UnsubscribeAllView(TokenAuthenticatedView):
    def get(self, request, username_b64, token):

        valid_token, username = check_token(username_b64, token)
        unsubscribe_successful = False

        if valid_token:
            user = get_object_or_404(CustomUser, username=username, is_active=True)
            email_preference, created = EmailPreference.objects.update_or_create(user=user,
                                                                                 defaults={'unsubscribe_all': True})
            unsubscribe_successful = email_preference is not None

        if not unsubscribe_successful:
            raise Exception('Unsubscribe all failed for user', (username, valid_token))

        return render(request, 'email_preference/unsubscribe_all_success.html', {})


class EmailPreferencesView(TokenAuthenticatedView):

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
