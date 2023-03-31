import logging
from datetime import datetime

from django.core import mail
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View

from rdrf.services.io.notifications.longitudinal_followups import send_longitudinal_followups

logger = logging.getLogger(__name__)


class MailboxView(View):
    def get(self, request):
        context = {}

        if hasattr(mail, 'outbox'):
            context['mail_messages'] = mail.outbox

        return render(request, 'debug/outbox.html', context)


class MailboxEmptyView(View):
    def get(self, request):
        if hasattr(mail, 'outbox'):
            mail.outbox = []

        return redirect(reverse('mailbox'))


class MailboxSendLongitudinalFollowups(View):
    def get(self, request):
        if now_param := request.GET.get('now', None):
            now = datetime.fromtimestamp(int(now_param))
        else:
            now = datetime.now()

        send_longitudinal_followups(now)

        return redirect(reverse('mailbox'))