from datetime import date

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import EmailTemplate, Registry, EmailNotification
from registry.groups.models import WorkingGroup
from registry.patients.models import AddressType, Patient, PatientAddress


class PatientViewBase(TestCase):
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
        self.registry.add_feature(RegistryFeatures.CONTEXTS)
        self.registry.save()
        self.working_group = WorkingGroup.objects.create(name='Test Working Group', registry=self.registry)

    def patient_post_data(self):
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
        return post_data

    def address(self, pk=None):
        return {
            "patient_address-TOTAL_FORMS": 1,
            "patient_address-INITIAL_FORMS": 1 if pk else 0,
            "patient_address-MIN_NUM_FORMS": 0,
            "patient_address-MAX_NUM_FORMS": 1000,

            "patient_address-0-id": pk or "",
            "patient_address-0-address_type": 1,
            "patient_address-0-address": "123 Leafy St",
            "patient_address-0-suburb": "Perth",
            "patient_address-0-country": "AU",
            "patient_address-0-state": "AU-WA",
            "patient_address-0-postcode": 6000,
        }

    def add_patient(self, address=None):
        post_data = self.patient_post_data()
        if address:
            post_data.update(address)
        self.client.login(username='admin', password='admin')
        response = self.client.post(
            reverse("patient_add", kwargs={"registry_code": self.registry.code}), post_data)
        return response

    def edit_patient(self, patient_pk, address=None):
        post_data = self.patient_post_data()
        if address:
            post_data.update(address)
        self.client.login(username='admin', password='admin')
        response = self.client.post(
            reverse("patient_edit", kwargs={"registry_code": self.registry.code, "patient_id": patient_pk}), post_data)
        return response

    def get_patient(self):
        return Patient.objects.filter(email=self.PATIENT_EMAIL).first()


class AddPatientViewTest(PatientViewBase):
    def test_new_patient_added(self):
        self.add_patient()
        patient = self.get_patient()
        self.assertIsNotNone(patient, "Patient not created !")


class PatientNotificationTest(PatientViewBase):
    def setUp(self):
        super().setUp()
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

    def test_NO_new_patient_registered_notification_on_add_patient(self):
        self.add_patient()
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

        self.add_patient()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.PATIENT_EMAIL])
        self.assertEqual(email.body, "Thanks for your participation!")


class EditPatientViewTest(PatientViewBase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.existing_patient = Patient.objects.create(
            family_name="Jim",
            given_names="Foo",
            consent=True,
            date_of_birth="1960-11-21",
        )
        PatientAddress.objects.create(
            patient=self.existing_patient,
            address_type=AddressType.objects.get(pk=2),
            address="1 Hilly St",
            suburb="Brisbane",
            country="AU",
            state="AU-QLD",
            postcode=4000,
        )

    def test_patient_edit_success(self):
        address_pk = self.existing_patient.patientaddress_set.first().pk
        self.edit_patient(self.existing_patient.pk, address=self.address(pk=address_pk))
        patient = Patient.objects.get(pk=self.existing_patient.pk)
        self.assertEqual(patient.family_name, "DOE")
        self.assertEqual(patient.given_names, "John")
        self.assertEqual(patient.date_of_birth, date.fromisoformat("2000-01-01"))

        self.assertEqual(patient.patientaddress_set.count(), 1)
        address = patient.patientaddress_set.first()
        self.assertEqual(address.address, "123 Leafy St")
        self.assertEqual(address.suburb, "Perth")
        self.assertEqual(address.state, "AU-WA")
        self.assertEqual(address.postcode, "6000")


class PatientAddressMandatoryFeatureTest(EditPatientViewTest):
    def setUp(self):
        super().setUp()
        self.registry.add_feature(RegistryFeatures.PATIENT_ADDRESS_IS_MANDATORY)
        self.registry.save()

    def test_validation_error_on_add_with_no_patient_address(self):
        response = self.add_patient()
        self.assertContains(response, 'Patient Address: Please submit at least 1 form.')
        self.assertIsNone(self.get_patient(), 'Patient was added without address!')

    def test_success_on_add_with_patient_address(self):
        self.add_patient(address=self.address())
        patient = self.get_patient()
        self.assertIsNotNone(patient, 'Patient not created!')
        self.assertEqual(patient.patientaddress_set.count(), 1)
        address = patient.patientaddress_set.first()
        self.assertEqual(address.address, '123 Leafy St')
        self.assertEqual(address.postcode, '6000')

    def test_validation_error_on_delete_of_single_patient_address(self):
        address_pk = self.existing_patient.patientaddress_set.first().pk
        address = self.address(pk=address_pk)
        address['patient_address-0-DELETE'] = 'on'
        response = self.edit_patient(self.existing_patient.pk, address=address)
        self.assertContains(response, 'Patient Address: Please submit at least 1 form.')
