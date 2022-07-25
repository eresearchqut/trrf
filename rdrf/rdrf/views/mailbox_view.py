import logging

from django.core import mail
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View

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
