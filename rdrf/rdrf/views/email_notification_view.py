import json
import logging

from django.apps import apps
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic.base import View

from rdrf.events.events import EventType
from rdrf.security.mixins import SuperuserRequiredMixin
from rdrf.services.io.notifications.email_notification import (
    EmailNotificationHistory,
    RdrfEmail,
)

logger = logging.getLogger(__name__)


class ResendEmail(SuperuserRequiredMixin, View):
    template_data = {}

    # TODO most of this code probably belongs on an EmailNotificationHistoryManager method
    # To be done as part of EmailNotificationHistory redesign #447
    def get(self, request, notification_history_id):
        self.notification_history_id = notification_history_id
        history = get_object_or_404(
            EmailNotificationHistory, pk=notification_history_id
        )

        self.template_data = history.template_data

        self._get_template_data()

        if EventType.is_registration(history.email_notification.description):
            self._ensure_registration_not_expired()

        email = RdrfEmail(
            language=history.language,
            email_notification=history.email_notification,
        )
        for key, value in self.template_data.items():
            email.append(key, value)
        if email.send():
            messages.add_message(request, messages.SUCCESS, "Email resend")
        else:
            messages.add_message(
                request, messages.ERROR, "Failure while resending email"
            )

        return redirect(
            reverse("admin:rdrf_emailnotificationhistory_changelist")
        )

    def _get_template_data(self):
        self.template_data = json.loads(self.template_data)
        for key, value in self.template_data.items():
            if isinstance(value, dict) and "app" in value and "model" in value:
                app = value.get("app")
                model = value.get("model")
                app_model = apps.get_model(app_label=app, model_name=model)
                self.template_data[key] = app_model.objects.get(
                    id=value.get("id")
                )

    def _ensure_registration_not_expired(self):
        registration = self.template_data.get("registration")
        if registration is None:
            logger.warn(
                'Template data for notification history %s should contain "registration" object',
                self.notification_history_id,
            )
            return
        user = registration.user
        if user.is_active:
            logger.info(
                'User "%s" already active. Not changing anything.', user
            )
            return
        registration.activated = False
        user.date_joined = timezone.now()
        registration.save()
        user.save()
        logger.info('Changed date_joined of user "%s" to today.', user)
