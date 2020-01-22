import logging

from django.conf import settings
from django.forms import Form, BooleanField, ChoiceField, CharField, TextInput, Select, Textarea
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

_form_attrs = {
    "class": "form-control",
}
RegistrationTextInput = TextInput(attrs=_form_attrs)
RegistrationSelectInput = Select(attrs=_form_attrs)
RegistrationTextAreaInput = Textarea(attrs=_form_attrs)

logger = logging.getLogger(__name__)


class RegistrationAdminForm(Form):
    enable_registration = BooleanField(
        required=False,
        label=_('Enable registration feature'),
    )
    new_notification = BooleanField(
        required=False,
        label=_('Create new email notifications for patients upon registration'),
    )
    notifications = None

    def __init__(self, notifications=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.notifications = []
        if notifications:
            for notification in notifications:
                self._add_notification(notification)

    def _add_notification(self, notification):
        self.notifications.append((notification.name, [template.language for template in notification.templates]))

        self.fields[f"{notification.name}_from_address"] = CharField(
            required=False,
            widget=RegistrationTextInput,
            label=_("From address")
        )
        self.fields[f"{notification.name}_disabled"] = BooleanField(
            required=False,
            label=_("Disabled")
        )

        for template in notification.templates:
            self.fields[f"{notification.name}_{template.language}_language"] = ChoiceField(
                required=False,
                choices=settings.ALL_LANGUAGES,
                widget=RegistrationSelectInput,
                label=_("Language")
            )
            self.fields[f"{notification.name}_{template.language}_description"] = CharField(
                required=False,
                widget=RegistrationTextInput,
                label=_("Description")
            )
            self.fields[f"{notification.name}_{template.language}_subject"] = CharField(
                required=False,
                max_length=50,
                widget=RegistrationTextInput,
                label=_("Subject")
            )
            self.fields[f"{notification.name}_{template.language}_body"] = CharField(
                required=False,
                widget=RegistrationTextAreaInput,
                label=_("Body")
            )

        self.initial[f"{notification.name}_from_address"] = notification.from_address
        self.initial[f"{notification.name}_disabled"] = notification.disabled
        self.initial[f"{notification.name}_templates"] = notification.templates

        for template in notification.templates:
            self.initial[f"{notification.name}_{template.language}_language"] = template.language
            self.initial[f"{notification.name}_{template.language}_description"] = template.description
            self.initial[f"{notification.name}_{template.language}_subject"] = template.subject
            self.initial[f"{notification.name}_{template.language}_body"] = template.body

    def render_notifications(self):
        html_output = []

        for name, template_languages in self.notifications:
            context = {
                "name": name,
                "from_address": self.__getitem__(f"{name}_from_address"),
                "disabled": self.__getitem__(f"{name}_disabled"),
                "templates": [
                    {
                        "language": self.__getitem__(f"{name}_{language}_language"),
                        "description": self.__getitem__(f"{name}_{language}_description"),
                        "subject": self.__getitem__(f"{name}_{language}_subject"),
                        "body": self.__getitem__(f"{name}_{language}_body"),
                    } for language in template_languages
                ]
            }
            html_output.append(render_to_string("admin/registration_setup_notification.html", context))

        return mark_safe("".join(html_output))
