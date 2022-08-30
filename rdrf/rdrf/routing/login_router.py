from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic.base import View
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ungettext

from useraudit.password_expiry import should_warn_about_password_expiry, days_to_password_expiry

from rdrf.services.io.notifications.email_notification import process_notification
from rdrf.events.events import EventType


# todo update ophg registries to use new demographics and patients listing
# forms: we need to fix this properly
def in_fkrp(user):
    user_reg_codes = [r.code for r in user.registry.all()]
    return "fkrp" in user_reg_codes


_PATIENTS_LISTING = "patientslisting"


class RouterView(View):

    def get(self, request):
        user = request.user

        if user.is_authenticated:
            redirect_url = user.default_page
        else:
            redirect_url = "%s?next=%s" % (reverse("two_factor:login"), reverse("login_router"))

        self._additional_checks(request)

        return redirect(redirect_url)

    def _additional_checks(self, request):
        self._maybe_warn_about_password_expiry(request)

    def _maybe_warn_about_password_expiry(self, request):
        user = request.user
        if not (user.is_authenticated and should_warn_about_password_expiry(user)):
            return

        days_left = days_to_password_expiry(user) or 0

        self._display_message(request, days_left)
        self._send_email_notification(user, days_left)

    def _display_message(self, request, days_left):
        sentence1 = ungettext(
            'Your password will expire in %(days)d day.',
            'Your password will expire in %(days)d days.', days_left) % {'days': days_left}
        link = f'<a href="{reverse("password_change")}" class="alert-link">{_("Change Password")}</a>'
        sentence2 = _('Please use %(link)s to change it.') % {'link': link}
        msg = sentence1 + ' ' + sentence2

        messages.warning(request, mark_safe(msg))

    def _send_email_notification(self, user, days_left):
        template_data = {
            'user': user,
            'days_left': days_left,
        }

        for registry_model in user.registry.all():
            process_notification(
                registry_model.code,
                EventType.PASSWORD_EXPIRY_WARNING,
                template_data)
