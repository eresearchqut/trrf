from dataclasses import dataclass
from typing import List

from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import ugettext as _


@dataclass
class NotificationTemplateData:
    language: settings.ALL_LANGUAGES
    description: str
    subject: str
    body: str


@dataclass
class NotificationData:
    # The address to send notifications from
    from_address: str

    # The list of templates
    templates: List[NotificationTemplateData]

    # The email address of the notification recipient (optional)
    recipient: str = ""

    # The name of the group recipient (optional)
    group_recipient: str = ""

    # Disable the notification
    disabled: bool = False


NOTIFICATIONS = [
    NotificationData(
        from_address="trrf@registryframework.net",
        recipient="{{ patient.user.email }}",
        disabled=False,
        templates=[
            NotificationTemplateData(
                language="en",
                description=_("Patient registration"),
                subject=f"{_('Welcome to the registry')}",
                body=get_template("registration/default_activation_body.html").template.source,
            ),
        ]
    ),
]
