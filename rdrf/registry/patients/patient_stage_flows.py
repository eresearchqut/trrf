import logging

from rdrf.helpers.registry_features import RegistryFeatures

from .constants import PatientState
from .models import PatientStageRule

logger = logging.getLogger(__name__)


class PatientStageFlow:

    def __init__(self, patient_state):
        self.patient_state = patient_state
        self.handlers = {
            PatientState.REGISTERED: self.handle_registered_patient,
            PatientState.CONSENTED: self.handle_consented_patient,
        }

    def handle_registered_patient(self, patient):
        rule = PatientStageRule.objects.filter(rule=self.patient_state, from_stage__isnull=True).first()
        logger.info(f"Handle registered patient for state {self.patient_state}, rule={rule}")
        if rule:
            patient.stage = rule.to_stage

    def handle_consented_patient(self, patient):
        rule = PatientStageRule.objects.filter(rule=self.patient_state, from_stage=patient.stage).first()
        logger.info(f"Handle consented patient for state {self.patient_state}, rule={rule}")
        if rule:
            patient.stage = rule.to_stage
            patient.save()

    def handle(self, registry, patient):
        if registry.has_feature(RegistryFeatures.STAGES):
            handler_func = self.handlers.get(self.patient_state, lambda self, patient: None)
            handler_func(patient)
