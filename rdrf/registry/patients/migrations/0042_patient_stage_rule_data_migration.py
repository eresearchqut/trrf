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
            metadata = json.loads(registry.metadata_json)
        except Exception:
            pass
    if "features" in metadata:
        return RegistryFeatures.STAGES in metadata["features"]
    else:
        return False

def applicable_to(apps, section, patient):
    if patient is None:
        return True
    if not section.applicability_condition:
            return True

    ParentGuardian = apps.get_model('patients', 'ParentGuardian')    
    self_patient = False
    try:
        ParentGuardian.objects.get(self_patient=patient)
        self_patient = True
    except ParentGuardian.DoesNotExist:
        pass

    function_context = {"patient": patient, "self_patient": self_patient}

    return eval(
        section.applicability_condition, {"__builtins__": None}, function_context
    )


def did_patient_provided_all_consent(apps, registry, patient):
    ConsentSection = apps.get_model('rdrf', 'ConsentSection')
    ConsentQuestion = apps.get_model('rdrf', 'ConsentQuestion')
    ConsentValue = apps.get_model('patients', 'ConsentValue')

    consent_questions = [q for sec in ConsentSection.objects.filter(registry=registry) if applicable_to(apps, sec, patient) for q in sec.questions.all()]

    def consent_answer(question):
        try:
            return ConsentValue.objects.get(patient=patient, consent_question=question).answer
        except ConsentValue.DoesNotExist:
            return False

    return all(consent_answer(q) for q in consent_questions)

def set_rules(apps, schema_editor):
    PatientStage = apps.get_model('patients', 'PatientStage')
    PatientStageRule = apps.get_model('patients', 'PatientStageRule')
    Patient = apps.get_model('patients', 'Patient')
    Registry = apps.get_model('rdrf', 'Registry')

    informed_consent = PatientStage.objects.filter(name='Informed Consent').first()
    eligibility = PatientStage.objects.filter(name='Eligibility').first()
    if informed_consent and eligibility:
        for reg in Registry.objects.all():
            if has_stages_feature(reg):
                PatientStageRule.objects.create(
                    registry=reg,
                    from_stage=None,
                    condition=PatientState.REGISTERED,
                    to_stage=informed_consent,
                    order=1
                )
                PatientStageRule.objects.create(
                    registry=reg,
                    from_stage=informed_consent,
                    condition=PatientState.CONSENTED,
                    to_stage=eligibility,
                    order=1
                )
                all_patients = Patient.objects.filter(rdrf_registry=reg)
                logger.info(f"Patients count for registry {reg}: {len(all_patients)} ")
                for patient in all_patients:
                    rule = PatientStageRule.objects.filter(condition=PatientState.REGISTERED, from_stage__isnull=True).first()
                    if rule:
                        logger.info(f"Apply {PatientState.REGISTERED} rule to {patient}")
                        patient.stage = rule.to_stage
                        patient.save()
                        if did_patient_provided_all_consent(apps, reg, patient):
                            rule = PatientStageRule.objects.filter(condition=PatientState.CONSENTED, from_stage=patient.stage).first()
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
