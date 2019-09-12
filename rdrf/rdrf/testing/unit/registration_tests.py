from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.models.definition.models import Registry, EmailNotification, ConsentSection, ConsentQuestion
from registry.patients.constants import PatientState
from registry.patients.models import Patient, PatientStage, PatientStageRule


class RegistrationTest(TestCase):

    fixtures = ['testing_auth', 'users', 'testing_rdrf']

    PATIENT_EMAIL = "john_doe@me.com"
    PATIENT_PWD = "12Password34%"

    def setUp(self):
        super().setUp()
        self.registry = Registry.objects.get(code='reg4')
        EmailNotification.objects.create(
            registry=self.registry,
            description=EventType.NEW_PATIENT,
            recipient='{{user.email}}',
            email_from='no-reply@reg4.net'
        )
        self.informed_consent, _ = PatientStage.objects.get_or_create(name="Informed consent")
        self.eligibility, _ = PatientStage.objects.get_or_create(name="Eligibility")
        self.informed_consent.allowed_next_stages.add(self.eligibility)
        self.eligibility.allowed_prev_stages.add(self.informed_consent)
        PatientStageRule.objects.create(
            from_stage=None,
            rule=PatientState.REGISTERED,
            to_stage=self.informed_consent
        )
        PatientStageRule.objects.create(
            from_stage=self.informed_consent,
            rule=PatientState.CONSENTED,
            to_stage=self.eligibility
        )

        self.consent_section = ConsentSection.objects.create(
            code='r4_cs',
            registry=self.registry,
            section_label='Consent Section',
            validation_rule='r4_cq'
        )
        self.consent_question = ConsentQuestion.objects.create(
            code='r4_cq',
            position=1,
            section=self.consent_section
        )

    def _register_patient(self):
        post_data = {
            "registry_code": "reg4",
            "email": self.PATIENT_EMAIL,
            "username": self.PATIENT_EMAIL,
            "password1": self.PATIENT_PWD,
            "password2": self.PATIENT_PWD,
            "first_name": "John",
            "surname": "Doe",
            "date_of_birth": "2000-01-01",
            "gender": "1",
            "address": "Test address",
            "suburb": "Brisbane",
            "country": "AU",
            "state": "AU-QLD",
            "postcode": "1234",
            "phone_number": "5678",
        }
        patch_method = "rdrf.views.registration_rdrf.RdrfRegistrationView.is_recaptcha_valid"
        with patch(patch_method, side_effect=lambda: True):
            response = self.client.post(reverse("registration_register", kwargs={"registry_code": self.registry.code}), post_data)
            self.assertEqual(response.status_code, 302)
            return Patient.objects.filter(email=self.PATIENT_EMAIL).first()


class PatientStageFlowTest(RegistrationTest):

    def _consent_post_data(self, patient):
        return {
            f"customconsent_{self.registry.id}_{self.consent_section.id}_{self.consent_question.id}": "on",
            "patient_consent_file-INITIAL_FORMS": 0,
            "patient_consent_file-TOTAL_FORMS": 0,
            "patient_consent_file-MIN_NUM_FORMS": 0,
            "patient_consent_file-MAX_NUM_FORMS": 0,
            "patient_consent_file-__prefix__-patient": patient.id
        }

    def test_patient_registration_stage(self):
        """
        When a patient is registered and stages are enabled the stage should be set
        to the first stage automatically
        """
        patient = self._register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(patient.stage, self.informed_consent)

    def test_patient_consent_stage_after_sign(self):
        """
        When the patient signs the consent and patient stages are enabled
        its stage should move to the next one
        """
        patient = self._register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(patient.stage, self.informed_consent)
        patient.user.is_active = True
        patient.user.save()
        logged_in = self.client.login(username=self.PATIENT_EMAIL, password=self.PATIENT_PWD)
        self.assertTrue(logged_in)
        response = self.client.post(
            reverse(
                'consent_form_view',
                kwargs={'registry_code': self.registry.code, "patient_id": patient.id}
            ), data=self._consent_post_data(patient)
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertEqual(patient.stage, self.eligibility)
