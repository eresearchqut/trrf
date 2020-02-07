"""Reference data like address types, etc.

Includes:
    - Address Types
"""
from django.template.loader import get_template

from rdrf.events.events import EventType
from rdrf.models.definition.models import EmailTemplate
from registry.patients.models import AddressType

deps = ['patient_stage']


def load_data(**kwargs):
    load_address_types()
    load_default_notifications()


def load_address_types():
    AddressType.objects.get_or_create(type="Home", description="Home Address")
    AddressType.objects.get_or_create(type="Postal", description="Postal Address")


def load_default_notifications():
    EmailTemplate.objects.get_or_create(
        language="en",
        description="trrf_default_patient_registration_en",
        subject="Welcome to the registry",
        body=get_template("registration/default_patient_registration_en.html").template.source,
        default_for_notification=EventType.NEW_PATIENT
    )
