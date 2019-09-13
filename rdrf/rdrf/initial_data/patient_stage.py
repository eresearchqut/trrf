"""
Initial treatment phases:
"""

from registry.patients import models
from rdrf.models.definition.models import Registry


def load_data(**kwargs):
    informed_consent = create_stage('Informed Consent', None)
    eligibility = create_stage('Eligibility', informed_consent)
    pre_screening = create_stage('Pre-screening', eligibility)
    screening = create_stage('Screening', pre_screening)
    run_in = create_stage('Run-in', screening)
    trial = create_stage('Trial', run_in)
    _ = create_stage('Follow-up', trial)
    for r in Registry.objects.all():
        create_rule(r, None, 'registered', informed_consent, 1)
        create_rule(r, informed_consent, 'consented', eligibility, 1)


def create_stage(name, previous_stage):
    stage, created = models.PatientStage.objects.get_or_create(name=name)
    if created and previous_stage:
        stage.allowed_prev_stages.add(previous_stage)
        previous_stage.allowed_next_stages.add(stage)
    return stage if created else None

def create_rule(registry, from_stage, rule, to_stage, order):
    models.PatientStageRule.objects.get_or_create(
        registry=registry,
        from_stage=from_stage, 
        condition=rule, 
        to_stage=to_stage,
        order=order
    )