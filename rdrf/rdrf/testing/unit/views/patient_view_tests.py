from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import EmailTemplate, Registry, EmailNotification
from registry.groups.models import WorkingGroup
from registry.patients.models import Patient


class AddPatientViewTest(TestCase):
    # fixtures = ['testing_auth', 'users', 'testing_rdrf']

    PATIENT_EMAIL = "john_doe@me.com"

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

        call_command('loaddata', 'testing_auth', **{'verbosity': 0, 'database': 'default'})
        call_command('loaddata', 'users', **{'verbosity': 0, 'database': 'default'})
        call_command('loaddata', 'testing_rdrf', **{'verbosity': 0, 'database': 'default'})

    def setUp(self):
        super().setUp()
        self.registry = Registry.objects.get(code='reg4')
        self.registry.add_feature(RegistryFeatures.PATIENTS_CREATE_USERS)
        self.registry.save()
        self.working_group = WorkingGroup.objects.create(name='Test Working Group', registry=self.registry)
        template = EmailTemplate.objects.create(
            language='en',
            description='New Patient Registered',
            subject='Welcome',
            body='Thanks for your registration!',
        )
        notification = EmailNotification.objects.create(
            registry=self.registry,
            description=EventType.NEW_PATIENT_USER_REGISTERED,
            recipient='{{patient.user.email}}',
            email_from='no-reply@reg4.net',
        )
        notification.email_templates.add(template)

    def add_patient(self):
        post_data = {
            "rdrf_registry": self.registry.pk,
            "working_groups": self.working_group.pk,
            "family_name": "Doe",
            "given_names": "John",
            "date_of_birth": "01-01-2000",
            "sex": 1,
            "living_status": "Alive",
            "email": self.PATIENT_EMAIL,
            "language_info-preferred_language": "en",
            "preferred_contact-contact_method": "email",
            "primary_carer-preferred_language": "en",
            "primary_carer-same_address": "on",

            "patient_address-TOTAL_FORMS": 0,
            "patient_address-INITIAL_FORMS": 0,
            "patient_address-MIN_NUM_FORMS": 0,
            "patient_address-MAX_NUM_FORMS": 1000,

        }
        self.client.login(username='admin', password='admin')
        response = self.client.post(reverse("patient_add", kwargs={"registry_code": self.registry.code}), post_data)
        self.assertEqual(response.status_code, 302)
        return Patient.objects.filter(email=self.PATIENT_EMAIL).first()


class PatientNotificationTest(AddPatientViewTest):

    def test_NO_new_patient_registered_notification_on_add_patient(self):
        patient = self.add_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(len(mail.outbox), 0)

    def test_new_patient_added_notification_on_add_patient(self):
        """
        When a patient is added to the registry only the NEW PATIENT ADDED notification is sent.
        """
        template = EmailTemplate.objects.create(
            language='en',
            description='New Patient Added',
            subject='Welcome',
            body='Thanks for your participation!',
        )
        notification = EmailNotification.objects.create(
            registry=self.registry,
            description=EventType.NEW_PATIENT_USER_ADDED,
            recipient='{{patient.user.email}}',
            email_from='no-reply@reg4.net',
        )
        notification.email_templates.add(template)

        patient = self.add_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.PATIENT_EMAIL])
        self.assertEqual(email.body, "Thanks for your participation!")
