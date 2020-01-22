from dataclasses import dataclass
from typing import List

from django.conf import settings
from django.utils.translation import ugettext as _


@dataclass
class NotificationTemplateData:
    language: settings.ALL_LANGUAGES
    description: str
    subject: str
    body: str


@dataclass
class NotificationData:
    # Unique name used in form to identify notification sections
    name: str

    # The address to send notifications from
    from_address: str

    # Disable the notification
    disabled: bool

    # The list of templates
    templates: List[NotificationTemplateData]


DEFAULT_NOTIFICATION_BODY = """<p>Dear {{patient.given_names}} {{patient.family_name|title}},</p>

<p>Thank you for registering.</p>

<p>Please click the following activation link to verify your account, or copy and paste into a web browser.</p>

<p><a href="{{ activation_url }}">Activation link</a></p>

<p>This link will expire in 2 days.</p>

<p>If needed, we will contact you by e-mail at {{patient.user.email}}.</p>

<p>Yours sincerely,<br>
The Registry Team</p>
"""

DEFAULT_NOTIFICATIONS = [
    NotificationData(
        name="Default",
        from_address="trrf@registryframework.net",
        disabled=False,
        templates=[
            NotificationTemplateData(
                language="en",
                description=_("Patient registration"),
                subject=f"{_('Welcome to the registry')}",
                body=DEFAULT_NOTIFICATION_BODY,
            ),
        ]
    ),
]
