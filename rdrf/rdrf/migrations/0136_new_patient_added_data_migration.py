# Generated by Django 2.2.25 on 2022-01-18 18:38

import logging

from django.db import migrations

from ..events.events import EventType


logger = logging.getLogger(__name__)


def replicate_new_patient_notifications(apps, schema_editor):
    EmailNotification = apps.get_model('rdrf', 'EmailNotification')
    notifications = EmailNotification.objects.filter(description=EventType.NEW_PATIENT)
    logger.info(f'Replicating {notifications.count()} "New Patient Registered" notifications')
    for notification in notifications:
        email_templates = notification.email_templates.all()
        notification.pk = None
        notification.description = EventType.NEW_PATIENT_ADDED
        notification.save()
        for template in email_templates:
            notification.email_templates.add(template)


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0135_new_patient_added_event_type'),
    ]

    operations = [
        migrations.RunPython(
            replicate_new_patient_notifications, reverse_code=migrations.RunPython.noop
        )
    ]

