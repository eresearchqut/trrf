# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import random

from django.db import migrations, models
from rdrf.helpers.registry_features import RegistryFeatures


def has_guid_feature(registry):
    metadata = {}
    if registry.metadata_json:
        try:
            metadata = json.loads(registry.metadata_json)
        except Exception:
            pass
    if "features" in metadata:
        return RegistryFeatures.PATIENT_GUID in metadata["features"]
    else:
        return False

def randomString(letters, length):
    return ''.join(random.choice(letters) for i in range(length))

def randomGUID():
    return randomString('ABCDEFGHJKLMNPRSTUVXYZ', 6) + randomString('123456789', 4)


def set_patients_guid(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    PatientGUID = apps.get_model('patients', 'PatientGUID')
    Registry = apps.get_model('rdrf', 'Registry')
    for p in Patient.objects.all():
        has_guid = any(has_guid_feature(r) for r in p.rdrf_registry.all())
        if has_guid and not PatientGUID.objects.filter(patient=p).exists():
            PatientGUID.objects.create(patient=p, guid=randomGUID())


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0045_patientguid'),
    ]

    operations = [
        migrations.RunPython(set_patients_guid, migrations.RunPython.noop)
    ]
