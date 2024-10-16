import json
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template import Context, Engine, Template
from django.template.loader import get_template
from registry.groups.models import CustomUser

from rdrf.auth.signed_url.util import make_token, make_token_authenticated_link
from rdrf.helpers.utils import make_full_url
from rdrf.models.definition.models import (
    EmailNotification,
    EmailNotificationHistory,
    EmailPreference,
    EmailTemplate,
)

logger = logging.getLogger(__name__)


class RdrfEmailException(Exception):
    pass


class RdrfEmail(object):
    _DEFAULT_LANGUAGE = "en"

    def __init__(
        self,
        reg_code=None,
        description=None,
        email_notification=None,
        language=None,
    ):
        self.email_from = None
        self.recipient_dict = {}  # Dict of email addresses with preferred language
        self.email_templates = []
        self.template_data = {}

        self.reg_code = reg_code
        self.description = description
        self.language = language  # used to only send to subset of languages by EmailNotificationHistory resend

        if email_notification:
            self.email_notification = email_notification
            self.reg_code = self.email_notification.registry.code
            self.description = self.email_notification.description

        else:
            self.email_notification = self._get_email_notification()

    def _send_mail(
        self, subject, body, address, recipient_list, html_message, headers=None
    ):
        mail = EmailMultiAlternatives(
            subject, body, address, recipient_list, headers
        )
        if html_message:
            mail.attach_alternative(html_message, "text/html")

        return mail.send()

    def send(self):
        success = False
        try:
            notification_record_saved = []
            recipients = self._get_recipients()
            if len(recipients) == 0:
                # If the recipient template does not evaluate to a valid email address this will be
                # true
                logger.debug("no recipients")
                return
            sender_address = (
                self.email_notification.email_from
                or settings.DEFAULT_FROM_EMAIL
            )
            for recipient in recipients:
                language = self._get_preferred_language(recipient)
                if self.language and self.language != language:
                    # skip recipients with diff language
                    # this is used in resend when we resend per language template
                    continue

                email_subject, email_body = self._get_email_subject_and_body(
                    language
                )

                if unsubscribe_footer := self._get_unsubscribe_footer(
                    recipient
                ):
                    email_body += unsubscribe_footer

                self._send_mail(
                    email_subject,
                    email_body,
                    sender_address,
                    [recipient],
                    html_message=email_body,
                )

                if language not in notification_record_saved:
                    self._save_notification_record(language)
                    notification_record_saved.append(language)
            logger.info("Sent email(s) %s" % self.description)
            logger.info("Email %s saved in history table" % self.description)
            success = True
        except RdrfEmailException as rdrfex:
            logger.error("RdrfEmailException: %s" % rdrfex)
            logger.warning(
                "No notification available for %s (%s)"
                % (self.reg_code, self.description)
            )
        return success

    def _get_user_from_email(self, email_address):
        return CustomUser.objects.get(email=email_address)

    def _get_preferred_language(self, email_address):
        def pref_lang():
            return self.template_data.get("preferred_language", "en")

        try:
            user_model = self._get_user_from_email(email_address)
            return user_model.preferred_language
        except (CustomUser.DoesNotExist, CustomUser.MultipleObjectsReturned):
            return self.recipient_dict.get(email_address, pref_lang())

    def _is_allowed_to_email(self, recipient):
        if self.email_notification.subscribable:
            try:
                user = self._get_user_from_email(recipient)
            except (
                CustomUser.DoesNotExist,
                CustomUser.MultipleObjectsReturned,
            ):
                return True  # recipient is not a standard user, therefore we don't know their email preferences

            email_preference = EmailPreference.objects.get_by_user(user)

            if email_preference and not email_preference.is_email_allowed(
                self.email_notification
            ):
                logger.debug(
                    f"User {user.id} does not allow emails for notification {self.email_notification.id}"
                )
                return False

        # By default, allow the email unless we have previously determined otherwise
        return True

    def _get_recipients(self):
        recipients = list(self.recipient_dict.keys()) or []
        if self.email_notification.recipient:
            recipient = self._get_recipient_template(
                self.email_notification.recipient
            )
            recipients.append(recipient)
        if self.email_notification.group_recipient:
            group_emails = self._get_group_emails(
                self.email_notification.group_recipient
            )
            recipients.extend(group_emails)

        # NB If a patient registers as a patient ( not a parent)
        # and a parent template is registered against the account verified
        # event , the recipient template will evaluate to an empty string ..

        return [
            r
            for r in recipients
            if self._valid_email(r) and self._is_allowed_to_email(r)
        ]

    def _valid_email(self, s):
        return "@" in s

    def _get_email_subject_and_body(self, language):
        try:
            email_template = self.email_notification.email_templates.get(
                language=language
            )
        except EmailTemplate.DoesNotExist:
            try:
                email_template = self.email_notification.email_templates.get(
                    language=self._DEFAULT_LANGUAGE
                )
            except EmailTemplate.DoesNotExist:
                raise RdrfEmailException(
                    "Can't find any email templates for Email notification %s"
                    % self.email_notification.id
                )

        context = Context(self.template_data)

        # Makes the full_url custom tag available in Email Templates without having to {% load full_url %}
        # full_url is like url but it returns the full URL so it doesn't have to be hardcoded into the templates.
        engine = Engine(builtins=["rdrf.templatetags.full_url"])

        template_subject = Template(email_template.subject)
        template_body = Template(email_template.body, engine=engine)

        template_subject = template_subject.render(context)
        template_body = template_body.render(context)

        return template_subject, template_body

    def _get_unsubscribe_footer(self, email_address):
        try:
            user = self._get_user_from_email(email_address)
            token = make_token(user.username)
            unsubscribe_all_url = make_token_authenticated_link(
                "unsubscribe_all", user.username, token
            )
            email_preferences_url = make_token_authenticated_link(
                "email_preferences", user.username, token
            )

            # Inject unsubscribe footer
            if self.email_notification.subscribable:
                full_unsubscribe_url = make_full_url(unsubscribe_all_url)
                unsubscribe_context = Context(
                    {
                        "unsubscribe_all_url": full_unsubscribe_url,
                        "email_preferences_url": make_full_url(
                            email_preferences_url
                        ),
                    }
                )
                template_footer = get_template(
                    "email_preference/_email_footer.html"
                )
                template_footer = template_footer.render(
                    unsubscribe_context.flatten()
                )
                return template_footer
        except (CustomUser.DoesNotExist, CustomUser.MultipleObjectsReturned):
            pass

        # This email does not require an unsubscribe footer
        return None

    def _get_email_notification(self):
        try:
            return EmailNotification.objects.get(
                registry__code=self.reg_code, description=self.description
            )
        except EmailNotification.DoesNotExist:
            raise RdrfEmailException()

    def _get_group_emails(self, group):
        user_emails = []
        users = CustomUser.objects.filter(groups__in=[group])

        for user in users:
            user_emails.append(user.email)

        return user_emails

    def _get_recipient_template(self, recipient):
        context = Context(self.template_data)
        recipient_template = Template(recipient)

        return recipient_template.render(context)

    def _save_notification_record(self, language):
        _template_data = {}

        for key, value in self.template_data.items():
            if value:
                if hasattr(value, "_meta") and hasattr(
                    getattr(value, "_meta"), "app_label"
                ):
                    _template_data[key] = {
                        "app": value._meta.app_label,
                        "model": value.__class__.__name__,
                        "id": value.id,
                    }
                else:
                    _template_data[key] = value

        enh = EmailNotificationHistory(
            language=language,
            email_notification=self.email_notification,
            template_data=json.dumps(_template_data),
        )
        enh.save()

    def append(self, key, obj):
        self.template_data[key] = obj
        return self


def process_given_notification(
    notification, template_data=None, mandatory_recipients=None
):
    if notification.disabled:
        logger.warning("Email %s disabled" % notification)
        return False
    else:
        logger.info("Sending email %s" % notification)
        email = RdrfEmail(email_notification=notification)
        email.recipient_dict = mandatory_recipients or {}
        email.template_data = template_data or {}
        return email.send()


def process_raw_email(
    subject, message_template, message_template_data, recipient_list
):
    email_body = message_template.render(
        Context(message_template_data).flatten()
    )

    return send_mail(
        subject=subject,
        message=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=email_body,
    )


def process_notification(
    reg_code=None,
    description=None,
    template_data=None,
    mandatory_recipients=None,
    default_template=None,
    default_subject=None,
):
    template_data = template_data or {}
    mandatory_recipients = mandatory_recipients or {}
    notes = EmailNotification.objects.filter(
        registry__code=reg_code, description=description
    )
    if notes:
        has_disabled = False
        sent_successfully = True
        for note in notes:
            if note.disabled:
                logger.warning("Email %s disabled" % note)
                has_disabled = True
                continue
            send_result = process_given_notification(
                note, template_data, mandatory_recipients
            )
            sent_successfully = sent_successfully and send_result
        return sent_successfully, has_disabled
    elif default_template:
        logger.debug("Registry notification not found, using default template")
        recipient_list = list(mandatory_recipients.keys())
        num_sent_emails = process_raw_email(
            default_subject, default_template, template_data, recipient_list
        )
        return (
            num_sent_emails > 0,
            False,
        )  # has sent successfully, wasn't disabled.
