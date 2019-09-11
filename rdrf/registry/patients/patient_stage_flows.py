from rdrf.helpers.registry_features import RegistryFeatures

from .constants import PatientState
from .models import PatientStage


class PatientStageFlow:

    def __init__(self, patient_state):
        self.patient_state = patient_state
        self.handlers = {
            PatientState.REGISTERED: self.handle_registered_patient,
            PatientState.CONSENTED: self.handle_consented_patient,
        }

    @staticmethod
    def handle_registered_patient(registry, patient):
        patient.stage = PatientStage.objects.filter(applicable_to=PatientState.REGISTERED).first()

    @staticmethod
    def handle_consented_patient(registry, patient):
        current_stage = patient.stage
        valid_stage = current_stage and current_stage.applicable_to == PatientState.REGISTERED
        if valid_stage:
            valid_next_stages = [
                s for s in current_stage.allowed_next_stages.all() if s.applicable_to == PatientState.CONSENTED
            ]
            if valid_next_stages:
                patient.stage = valid_next_stages[0]
                patient.save()

    def handle(self, registry, patient):
        if registry.has_feature(RegistryFeatures.STAGES):
            handler_func = self.handlers.get(self.patient_state, lambda registry, patient: None)
            handler_func(registry, patient)
