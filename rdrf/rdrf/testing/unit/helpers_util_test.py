from django.test import TestCase

from rdrf.helpers.utils import consent_status_for_patient_consent
from rdrf.models.definition.models import Registry, ConsentSection, ConsentQuestion
from registry.patients.models import Patient, ConsentValue


def create_valid_patient(registries=None):
    patient = Patient.objects.create(consent=True, date_of_birth='1999-12-12')
    patient.rdrf_registry.set(registries)
    return patient


class HelpersUtilTest(TestCase):

    def test_consent_status_for_patient_consent(self):
        registry_1 = Registry.objects.create(code='REG-1')
        consent_section_1 = ConsentSection.objects.create(registry=registry_1, code='S1', section_label='S1')
        consent_section_2 = ConsentSection.objects.create(registry=registry_1, code='S2', section_label='S2')
        consent_question_1 = ConsentQuestion.objects.create(section=consent_section_1, code='Q1', question_label='Q1')
        consent_question_2 = ConsentQuestion.objects.create(section=consent_section_1, code='Q2', question_label='Q2')
        consent_question_3 = ConsentQuestion.objects.create(section=consent_section_2, code='Q3', question_label='Q3')

        registry_2 = Registry.objects.create(code='REG-2')
        consent_section_3 = ConsentSection.objects.create(registry=registry_2, code='S3', section_label='S3')
        consent_question_4 = ConsentQuestion.objects.create(section=consent_section_3, code='Q1', question_label='Q1')
        consent_question_5 = ConsentQuestion.objects.create(section=consent_section_3, code='Q2', question_label='Q2')

        patient_1 = create_valid_patient([registry_1])
        patient_2 = create_valid_patient([registry_2])
        patient_3 = create_valid_patient([registry_1, registry_2])
        patient_4 = create_valid_patient([])

        ConsentValue.objects.create(patient_id=patient_1.id, consent_question=consent_question_1, answer=True)
        ConsentValue.objects.create(patient_id=patient_1.id, consent_question=consent_question_3, answer=False)
        ConsentValue.objects.create(patient_id=patient_2.id, consent_question=consent_question_4, answer=True)
        ConsentValue.objects.create(patient_id=patient_2.id, consent_question=consent_question_5, answer=False)
        ConsentValue.objects.create(patient_id=patient_3.id, consent_question=consent_question_1, answer=True)
        ConsentValue.objects.create(patient_id=patient_3.id, consent_question=consent_question_2, answer=True)
        ConsentValue.objects.create(patient_id=patient_3.id, consent_question=consent_question_3, answer=True)
        ConsentValue.objects.create(patient_id=patient_3.id, consent_question=consent_question_5, answer=True)

        # Patients have consented to consent question
        self.assertTrue(consent_status_for_patient_consent(registry_1, patient_1.id, 'Q1'))
        self.assertTrue(consent_status_for_patient_consent(registry_2, patient_2.id, 'Q1'))
        self.assertTrue(consent_status_for_patient_consent(registry_1, patient_3.id, 'Q1'))
        self.assertTrue(consent_status_for_patient_consent(registry_1, patient_3.id, 'Q2'))

        # Patients have NOT consented to consent question

        # --> unanswered (e.g. new question added after they had already completed their consent, or not in the same registry)
        self.assertFalse(consent_status_for_patient_consent(registry_1, patient_2.id, 'Q1'))
        self.assertFalse(consent_status_for_patient_consent(registry_1, patient_4.id, 'Q1'))

        self.assertFalse(consent_status_for_patient_consent(registry_2, patient_1.id, 'Q1'))
        self.assertFalse(consent_status_for_patient_consent(registry_2, patient_3.id, 'Q1'))

        # --> specifically not consented
        self.assertFalse(consent_status_for_patient_consent(registry_1, patient_1.id, 'Q3'))

        # --> they have consented to a question in another registry that shares the same question code.
        self.assertFalse(consent_status_for_patient_consent(registry_2, patient_2.id, 'Q2'))

        # consent question code does not exist
        self.assertFalse(consent_status_for_patient_consent(registry_1, patient_1.id, 'NO_MATCH'))
