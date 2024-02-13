# Generated by Django 3.2.23 on 2024-02-13 11:06
import logging
import uuid

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations

logger = logging.getLogger(__name__)


def migrate_consentfile_location(apps, schema_editor):
    PatientConsent = apps.get_model('patients', 'PatientConsent')
    consents = PatientConsent.objects.all().order_by("id")

    for consent in consents:
        new_filename = str(uuid.uuid4())
        original_file = consent.form
        original_path = original_file.name
        if default_storage.exists(original_file.name):
            consent.filename = new_filename
            consent.form = File(original_file, name=consent.original_filename)
            consent.save()
            logger.info(f'id={consent.id} - COMPLETED: original_path={original_path}, new_path={consent.form.name}')
        else:
            logger.info(f'id={consent.id} - FAILED: could not find original_path={original_path}')


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0063_patientconsent_original_filename'),
    ]

    operations = [
        migrations.RunPython(
            migrate_consentfile_location, migrations.RunPython.noop
        ),
    ]
