from base64 import b32decode

from django_otp.oath import totp

from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import EmailTemplate, Registry


def close_registration(registry_name):
    registry = Registry.objects.get(name=registry_name)
    if registry.has_feature(RegistryFeatures.REGISTRATION):
        registry.remove_feature(RegistryFeatures.REGISTRATION)
        registry.save()


def open_registration(registry_name):
    registry = Registry.objects.get(name=registry_name)

    if not registry.has_feature(RegistryFeatures.REGISTRATION):
        registry.add_feature(RegistryFeatures.REGISTRATION)
        registry.save()

    if not registry.emailnotification_set.filter(
        description__in=EventType.REGISTRATION_TYPES
    ):
        email_template = EmailTemplate.objects.create(
            language="en",
            subject="Welcome to the registry",
            body="Activation link: {{ activation_url }}",
        )
        email_notification = registry.emailnotification_set.create(
            description=EventType.NEW_PATIENT_USER_REGISTERED,
            recipient="{{patient.user.email}}",
            email_from="no-reply@registryframework.net",
        )
        email_notification.email_templates.add(email_template)
        email_notification.save()


def set_otp_token(page, key):
    token = str(totp(b32decode(key.encode())))
    page.set_token(token).submit()
