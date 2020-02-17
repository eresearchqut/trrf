from django.template.loader import get_template

from rdrf.events.events import EventType
from rdrf.models.definition.models import EmailTemplate


def load_data(**kwargs):
    load_default_patient_registration_template()


def load_default_patient_registration_template():
    EmailTemplate.objects.get_or_create(
        language="en",
        description="Default patient registration notification",
        subject="Welcome to the registry",
        body=get_template("registration/default_patient_registration_en.html").template.source,
        default_for_notification=EventType.NEW_PATIENT
    )
