import logging
from datetime import datetime
from datetime import timezone as dt_timezone

from django.core import mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from rdrf.services.io.notifications.longitudinal_followups import (
    send_longitudinal_followups,
)

logger = logging.getLogger(__name__)


class MailboxView(View):
    def get(self, request):
        context = {}

        if hasattr(mail, "outbox"):
            context["mail_messages"] = mail.outbox

        return render(request, "debug/outbox.html", context)


class MailboxEmptyView(View):
    def get(self, request):
        if hasattr(mail, "outbox"):
            mail.outbox = []

        return redirect(reverse("mailbox"))


class MailboxSendLongitudinalFollowups(View):
    def get(self, request):
        if now_param := request.GET.get("now", None):
            # Use Python's datetime.timezone.utc directly for clarity
            now = datetime.fromtimestamp(int(now_param), tz=dt_timezone.utc)
        else:
            now = timezone.now()

        logger.info(f"Sending longitudinal followups with now={now}")
        send_longitudinal_followups(now)

        return redirect(reverse("mailbox"))
