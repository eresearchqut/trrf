"""
Initial treatment phases:
"""

from registry.patients import models


def load_data(**kwargs):
    informed_consent = create_stage('Informed Consent', None)
    eligibility = create_stage('Eligibility', informed_consent)
    pre_screening = create_stage('Pre-screening', eligibility)
    screening = create_stage('Screening', pre_screening)
    run_in = create_stage('Run-in', screening)
    trial = create_stage('Trial', run_in)
    _ = create_stage('Follow-up', trial)
    create_rule(None, 'registered', informed_consent)
    create_rule(informed_consent, 'consented', eligibility)


def create_stage(name, previous_stage):
    stage, created = models.PatientStage.objects.get_or_create(name=name)
    if created and previous_stage:
        stage.allowed_prev_stages.add(previous_stage)
        previous_stage.allowed_next_stages.add(stage)
    return stage if created else None

def create_rule(from_stage, rule, to_stage):
    models.PatientStageRule.objects.get_or_create(from_stage=from_stage, rule=rule, to_stage=to_stage)