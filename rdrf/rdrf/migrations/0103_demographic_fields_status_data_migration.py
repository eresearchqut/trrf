# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from django.db import migrations, models


HIDDEN = 2
READONLY = 1


def migrate_to_status(apps, schema_editor):
    DemographicFields = apps.get_model('rdrf', 'demographicfields')
    for entry in DemographicFields.objects.all():
        entry.status = HIDDEN if entry.hidden else READONLY
        entry.save()


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0102_demographic_fields_status'),
    ]

    operations = [
        migrations.RunPython(migrate_to_status, migrations.RunPython.noop)
    ]
