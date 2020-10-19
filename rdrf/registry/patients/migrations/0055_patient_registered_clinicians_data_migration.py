# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.db import migrations, models


def migrate_patient_clinician(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    CustomUser = apps.get_model('groups', 'CustomUser')

    qs = Patient.objects.filter(clinician__isnull=False)
    for p in qs:
        p.registered_clinicians.set([p.clinician])


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0054_patient_registered_clinicians'),
    ]

    operations = [
        migrations.RunPython(migrate_patient_clinician, migrations.RunPython.noop)
    ]
