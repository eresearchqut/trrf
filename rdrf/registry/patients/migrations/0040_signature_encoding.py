# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import json
from django.db import migrations, models


def encode_signatures(apps, schema_editor):
    PatientSignature = apps.get_model('patients', 'PatientSignature')
    for row in PatientSignature.objects.all():
        signature = row.signature
        row.signature = base64.b64encode(signature.encode('utf-8')).decode('utf-8')
        row.save()


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0039_patient_signature'),
    ]

    operations = [
        migrations.RunPython(encode_signatures, migrations.RunPython.noop)
    ]
