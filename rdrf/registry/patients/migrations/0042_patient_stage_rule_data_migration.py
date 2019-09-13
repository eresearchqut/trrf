# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from django.db import migrations, models
from registry.patients.constants import PatientState
from rdrf.helpers.registry_features import RegistryFeatures

logger = logging.getLogger(__name__)

def has_stages_feature(registry):
    metadata = {}
    if registry.metadata_json:
        try:
            metadata = json.loads(self.metadata_json)
        except Exception:
            pass
    if "features" in metadata:
        return RegistryFeatures.STAGES in metadata["features"]
    else:
        return False


def set_rules(apps, schema_editor):
    PatientStage = apps.get_model('patients', 'PatientStage')
    PatientStageRule = apps.get_model('patients', 'PatientStageRule')
    Patient = apps.get_model('patients', 'Patient')

    informed_consent = PatientStage.objects.filter(name='Informed Consent').first()
    eligibility = PatientStage.objects.filter(name='Eligibility').first()
    if informed_consent and eligibility:
        PatientStageRule.objects.create(
            from_stage=None,
            rule=PatientState.REGISTERED,
            to_stage=informed_consent
        )
        PatientStageRule.objects.create(
            from_stage=informed_consent,
            rule=PatientState.CONSENTED,
            to_stage=eligibility
        )
        all_patients = Patient.objects.all()
        logger.info(f"Patients count: {len(all_patients)}")
        for patient in all_patients:
            for reg in patient.rdrf_registry.all():
                if has_stages_feature(reg):
                    # Handle registered patients
                    rule = PatientStageRule.objects.filter(rule=PatientState.REGISTERED, from_stage__isnull=True).first()
                    if rule:
                        logger.info(f"Apply {PatientState.REGISTERED} rule to {patient}")
                        patient.stage = rule.to_stage
                        patient.save()
                        if patient.consent:
                            rule = PatientStageRule.objects.filter(rule=PatientState.CONSENTED, from_stage=patient.stage).first()
                            if rule:
                                logger.info(f"Apply {PatientState.CONSENTED} rule to {patient}")
                                patient.stage = rule.to_stage
                                patient.save()


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0041_patient_stage_rule'),
    ]

    operations = [
        migrations.RunPython(set_rules, migrations.RunPython.noop)
    ]
