# Generated by Django 2.2.25 on 2022-01-20 17:01

import json
import logging

from django.db import migrations

from ..events.events import EventType
from ..helpers.registry_features import RegistryFeatures


logger = logging.getLogger(__name__)


def update_new_patient_event_type(apps, schema_editor):
    EmailNotification = apps.get_model('rdrf', 'EmailNotification')
    OLD_TYPE = 'new-patient'
    notifications = EmailNotification.objects.filter(description=OLD_TYPE)
    logger.info(f'Updating {notifications.count()} "New Patient Registered" notifications')
    for notification in notifications:
        notification.description = EventType.NEW_PATIENT_USER_REGISTERED
        notification.save()


def load_metadata(registry):
    try:
        return json.loads(registry.metadata_json)
    except ValueError:
        logger.warn(f"Couldn't load metadata of registry '{registry.code}'!")
    return {}


def has_feature(registry, feature):
    metadata = load_metadata(registry)
    return feature in metadata.get('features', [])


def should_replicate(notification):
    return has_feature(notification.registry, RegistryFeatures.PATIENTS_CREATE_USERS)


def replicate_new_patient_notifications(apps, schema_editor):
    EmailNotification = apps.get_model('rdrf', 'EmailNotification')
    notifications = [n for n in EmailNotification.objects.filter(description=EventType.NEW_PATIENT_USER_REGISTERED) if should_replicate(n)]
    logger.info(f'Replicating {len(notifications)} "New Patient Registered" notifications')
    for notification in notifications:
        email_templates = notification.email_templates.all()
        notification.pk = None
        notification.description = EventType.NEW_PATIENT_USER_ADDED
        notification.save()
        for template in email_templates:
            notification.email_templates.add(template)


def migrate(apps, schema_editor):
    update_new_patient_event_type(apps, schema_editor)
    replicate_new_patient_notifications(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0135_split_new_patient_event_types'),
    ]

    operations = [
        migrations.RunPython(
            migrate, reverse_code=migrations.RunPython.noop
        )
    ]

