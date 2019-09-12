# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_rules(apps, schema_editor):
    PatientStage = apps.get_model('patients', 'PatientStage')
    PatientStageRule = apps.get_model('patients', 'PatientStageRule')

    informed_consent = PatientStage.objects.filter(name='Informed Consent').first()
    eligibility = PatientStage.objects.filter(name='Eligibility').first()
    if informed_consent and eligibility:
        PatientStageRule.objects.create(
            from_stage=None,
            rule='registered',
            to_stage=informed_consent
        )
        PatientStageRule.objects.create(
            from_stage=informed_consent,
            rule='registered',
            to_stage=eligibility
        )

class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0041_patient_stage_rule'),
    ]

    operations = [
        migrations.RunPython(set_rules, migrations.RunPython.noop)
    ]
