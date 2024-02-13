# Generated by Django 3.2.23 on 2024-02-07 14:08
import logging
import uuid

from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations

logger = logging.getLogger(__name__)


def migrate_cdefile_location(apps, schema_editor):
    CDEFile = apps.get_model('rdrf', 'CDEFile')
    cde_files = CDEFile.objects.all().order_by("id")

    for cde_file in cde_files:
        new_filename = str(uuid.uuid4())
        original_file = cde_file.item
        original_path = original_file.name
        if default_storage.exists(original_file.name):
            cde_file.filename = new_filename
            cde_file.item = File(original_file, name=cde_file.original_filename)
            cde_file.save()
            logger.info(f'id={cde_file.id} - COMPLETED: original_path={original_path}, new_path={cde_file.item.name}')
        else:
            logger.info(f'id={cde_file.id} - FAILED: could not find original_path={original_path}')


class Migration(migrations.Migration):
    dependencies = [
        ('rdrf', '0168_cdefile_original_filename'),
    ]

    operations = [
        migrations.RunPython(
            migrate_cdefile_location, migrations.RunPython.noop
        ),
    ]
