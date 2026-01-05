import logging

from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.contrib.messages.storage import default_storage
from django.dispatch import receiver
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django_otp import devices_for_user
from two_factor import forms as tff
from two_factor import views as tfv
from two_factor.utils import default_device

from rdrf.auth import is_user_privileged
from rdrf.models.definition.models import Registry

from .forms import (
    LoginAuthenticationForm,
)

logger = logging.getLogger(__name__)


@method_decorator(sensitive_post_parameters(), name="dispatch")
@method_decorator(never_cache, name="dispatch")
class LoginView(tfv.LoginView):
    form_list = (
        ("auth", LoginAuthenticationForm),
        ("token", tff.AuthenticationTokenForm),
        ("backup", tff.BackupTokenForm),
    )

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context["registries_with_registration"] = [
            registry
            for registry in Registry.objects.all()
            if registry.registration_allowed()
        ]
        return context


@receiver(user_logged_in)
def user_login_callback(sender, request=None, user=None, **kwargs):
    if (
        is_user_privileged(user)
        and not user.require_2_fact_auth
        and default_device(user) is None
    ):
        link = '<a href="%(url)s" class="alert-link">%(link_text)s</a>' % {
            "url": reverse("two_factor:setup"),
            "link_text": _("click here"),
        }
        msg = mark_safe(
            _(
                "We strongly recommend that you protect your account with Two-Factor authentication. "
                "Please %(link)s to set it up."
            )
            % {"link": link}
        )

        if not hasattr(request, "_messages"):
            # Workaround for tests when privileged users log in
            request._messages = default_storage(request)

        if msg not in [m.message for m in messages.get_messages(request)]:
            messages.info(request, msg)
    if user.force_password_change:
        messages.info(
            request,
            _("You are required to change your password for security purposes"),
        )


# Customised Two Factor views


@method_decorator(never_cache, name="dispatch")
class QRGeneratorView(tfv.core.QRGeneratorView):
    session_key_name = "two_fact_auth_key"


@method_decorator(never_cache, name="dispatch")
class SetupView(tfv.core.SetupView):
    session_key_name = "two_fact_auth_key"


@method_decorator(never_cache, name="dispatch")
class DisableView(tfv.profile.DisableView):
    def form_valid(self, form):
        user = self.request.user
        for device in devices_for_user(user):
            device.delete()

        return redirect(user.default_page)
