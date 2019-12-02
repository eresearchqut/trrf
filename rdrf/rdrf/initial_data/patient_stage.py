"""
Initial treatment phases:
"""

from registry.patients import models
from rdrf.models.definition.models import Registry
from rdrf.helpers.registry_features import RegistryFeatures


def load_data(**kwargs):
    for r in Registry.objects.all():
        if r.has_feature(RegistryFeatures.STAGES):
            init_registry_stages_and_rules(r)

def init_registry_stages_and_rules(registry):
        informed_consent = create_stage(registry, 'Informed Consent', None)
        eligibility = create_stage(registry, 'Eligibility', informed_consent)
        pre_screening = create_stage(registry, 'Pre-screening', eligibility)
        screening = create_stage(registry, 'Screening', pre_screening)
        run_in = create_stage(registry, 'Run-in', screening)
        trial = create_stage(registry, 'Trial', run_in)
        _ = create_stage(registry, 'Follow-up', trial)
        if informed_consent and eligibility:
            create_rule(registry, None, 'registered', informed_consent, 1)
            create_rule(registry, informed_consent, 'consented', eligibility, 1)

def create_stage(registry, name, previous_stage):
    stage, created = models.PatientStage.objects.get_or_create(name=name, registry=registry)
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