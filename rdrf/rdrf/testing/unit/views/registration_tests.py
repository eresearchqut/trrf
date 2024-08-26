from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from registry.patients.constants import PatientState
from registry.patients.models import Patient, PatientStage, PatientStageRule

from rdrf.events.events import EventType
from rdrf.models.definition.models import (
    ConsentQuestion,
    ConsentSection,
    EmailNotification,
    EmailTemplate,
    Registry,
)


class RegistrationTest(TestCase):
    databases = ["default", "clinical"]
    # fixtures = ['testing_auth', 'users', 'testing_rdrf']

    PATIENT_EMAIL = "john_doe@me.com"
    PATIENT_PWD = "12Password34%"

    @classmethod
    def setUpClass(cls):
        # Try fixme when moving to >= Django 3.1
        # See https://docs.djangoproject.com/en/2.2/topics/testing/tools/#multi-database-support
        #
        # Django 2.2 tries to load the fixtures (commented out above) into both databases
        # using the router. Because our models use natural keys, the data is not being
        # deserialized correctly, and causes an exception
        #
        # Therefore we must call the loaddata command manually like so, rather than using
        # the loop in TestCase.setUpClass
        super().setUpClass()

        call_command(
            "loaddata",
            "testing_auth",
            **{"verbosity": 0, "database": "default"},
        )
        call_command(
            "loaddata", "users", **{"verbosity": 0, "database": "default"}
        )
        call_command(
            "loaddata",
            "testing_rdrf",
            **{"verbosity": 0, "database": "default"},
        )

    def setUp(self):
        super().setUp()
        self.registry = Registry.objects.get(code="reg4")
        template = EmailTemplate.objects.create(
            language="en",
            description="New Patient Registered",
            subject="Welcome",
            body="Thanks for your registration!",
        )
        notification = EmailNotification.objects.create(
            registry=self.registry,
            description=EventType.NEW_PATIENT_USER_REGISTERED,
            recipient="{{patient.user.email}}",
            email_from="no-reply@reg4.net",
        )
        notification.email_templates.add(template)

        self.informed_consent, _ = PatientStage.objects.get_or_create(
            registry=self.registry, name="Informed Consent"
        )
        self.eligibility, _ = PatientStage.objects.get_or_create(
            registry=self.registry, name="Eligibility"
        )
        self.informed_consent.allowed_next_stages.add(self.eligibility)
        self.eligibility.allowed_prev_stages.add(self.informed_consent)
        PatientStageRule.objects.get_or_create(
            registry=self.registry,
            from_stage=None,
            condition=PatientState.REGISTERED,
            to_stage=self.informed_consent,
            order=1,
        )
        PatientStageRule.objects.get_or_create(
            registry=self.registry,
            from_stage=self.informed_consent,
            condition=PatientState.CONSENTED,
            to_stage=self.eligibility,
            order=1,
        )

        self.consent_section = ConsentSection.objects.create(
            code="r4_cs",
            registry=self.registry,
            section_label="Consent Section",
            validation_rule="r4_cq",
        )
        self.consent_question = ConsentQuestion.objects.create(
            code="r4_cq", position=1, section=self.consent_section
        )

    def register_patient(self):
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
            response = self.client.post(
                reverse(
                    "registration_register",
                    kwargs={"registry_code": self.registry.code},
                ),
                post_data,
            )
            self.assertEqual(response.status_code, 302)
            return Patient.objects.filter(email=self.PATIENT_EMAIL).first()

    def consent_post_data(self, patient):
        return {
            f"customconsent_{self.registry.id}_{self.consent_section.id}_{self.consent_question.id}": "on",
            "patient_consent_file-INITIAL_FORMS": 0,
            "patient_consent_file-TOTAL_FORMS": 0,
            "patient_consent_file-MIN_NUM_FORMS": 0,
            "patient_consent_file-MAX_NUM_FORMS": 0,
            "patient_consent_file-__prefix__-patient": patient.id,
        }


class PatientNotificationTest(RegistrationTest):
    def test_new_patient_registered_notification_sent_on_registration(self):
        """
        When a patient is registered a NEW PATIENT USER REGISTERED notification should be sent if set up properly.
        """
        patient = self.register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.PATIENT_EMAIL])

    def test_new_patient_added_notification_NOT_sent_on_registration(self):
        """
        When a patient is registered a NEW PATIENT USER ADDED notification should NOT be sent if set up properly.
        """
        notification = EmailNotification.objects.first()
        notification.description = EventType.NEW_PATIENT_USER_ADDED
        notification.pk = None
        notification.save()
        patient = self.register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(len(mail.outbox), 1)


class PatientStageFlowTest(RegistrationTest):
    def test_patient_registration_stage(self):
        """
        When a patient is registered and stages are enabled the stage should be set
        to the first stage automatically
        """
        patient = self.register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(patient.stage, self.informed_consent)

    def test_patient_consent_stage_after_sign(self):
        """
        When the patient signs the consent and patient stages are enabled
        its stage should move to the next one
        """
        patient = self.register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(patient.stage, self.informed_consent)
        patient.user.is_active = True
        patient.user.save()
        logged_in = self.client.login(
            username=self.PATIENT_EMAIL, password=self.PATIENT_PWD
        )
        self.assertTrue(logged_in)
        response = self.client.post(
            reverse(
                "consent_form_view",
                kwargs={
                    "registry_code": self.registry.code,
                    "patient_id": patient.id,
                },
            ),
            data=self.consent_post_data(patient),
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        self.assertEqual(patient.stage, self.eligibility)
