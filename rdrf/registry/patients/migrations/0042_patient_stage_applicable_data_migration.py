# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import json
from django.db import migrations, models


def set_applicable_to(apps, schema_editor):
    PatientStage = apps.get_model('patients', 'PatientStage')
    PatientStage.objects.filter(name='Informed Consent').update(applicable_to='registered')
    PatientStage.objects.filter(name='Eligibility').update(applicable_to='consented')


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0041_patientstage_applicable_to'),
    ]

    operations = [
        migrations.RunPython(set_applicable_to, migrations.RunPython.noop)
    ]
