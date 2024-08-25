import logging

from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import ConsentSection
from registry.patients.models import ConsentValue

from .constants import PatientState
from .models import PatientStageRule

logger = logging.getLogger(__name__)


def get_registry_stage_flow(registry):
    if not registry.has_feature(RegistryFeatures.STAGES):
        return PatientNoStageFlow()
    return PatientStageFlow(registry)


def is_patient_registered(registry, patient):
    # All exisiting patients are registered, as long as they are in the registry
    return patient.rdrf_registry.filter(pk=registry.pk).exists()


def did_patient_provided_all_consent(registry, patient):
    consent_questions = [
        q
        for sec in ConsentSection.objects.filter(registry=registry)
        if sec.applicable_to(patient)
        for q in sec.questions.all()
    ]

    def consent_answer(question):
        try:
            return ConsentValue.objects.get(
                patient=patient, consent_question=question
            ).answer
        except ConsentValue.DoesNotExist:
            return False

    return all(consent_answer(q) for q in consent_questions)


class PatientNoStageFlow:
    def handle(self, patient):
        return False


class PatientStageFlow:
    CONDITION_HANDLERS = {
        PatientState.REGISTERED: is_patient_registered,
        PatientState.CONSENTED: did_patient_provided_all_consent,
    }

    def __init__(self, registry):
        self.registry = registry

    def evaluate_condition(self, patient, condition):
        return self.CONDITION_HANDLERS[condition](self.registry, patient)

    def handle(self, patient):
        for rule in (
            PatientStageRule.objects.filter(
                from_stage=patient.stage, registry=self.registry
            )
            .order_by("order")
            .all()
        ):
            if self.evaluate_condition(patient, rule.condition):
                logger.info(
                    f"Moving patient {patient.pk} in registry {self.registry} "
                    f"from stage {rule.from_stage} to {rule.to_stage} "
                    f"based on rule {rule.condition}"
                )
                patient.stage = rule.to_stage
                patient.save()
                return True
        return False
