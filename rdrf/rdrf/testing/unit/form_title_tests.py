from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from rdrf.events.events import EventType
from django.contrib.auth.models import Group
from rdrf.models.definition.models import FormTitle

from .registration_tests import RegistrationTest


class FormTitleTest(RegistrationTest):

    def setUp(self):
        super().setUp()
        ft = FormTitle.objects.create(
            registry=self.registry,
            default_title=FormTitle.FORM_TITLE_CHOICES[0][0],
            custom_title="Demographics-updated",
            order=1
        )
        g = Group.objects.get(name='Patients')
        ft.groups.add(g)
        ft.save()

    def test_form_title_when_patient_logs_in(self):
        """
        When the patient signs in the custom Demographic title should be displayed.
        Admins should see the default title.
        """
        patient = self.register_patient()
        self.assertIsNotNone(patient, "Patient not created !")
        patient.user.is_active = True
        patient.user.save()
        logged_in = self.client.login(username=self.PATIENT_EMAIL, password=self.PATIENT_PWD)
        self.assertTrue(logged_in)
        response = self.client.post(
            reverse(
                'consent_form_view',
                kwargs={'registry_code': self.registry.code, "patient_id": patient.id}
            ), data=self.consent_post_data(patient)
        )
        self.assertEqual(response.status_code, 302)
        patient.refresh_from_db()
        response = self.client.get(
            reverse(
                'patient_edit',
                kwargs={'registry_code': self.registry.code, "patient_id": patient.id}
            )
        )
        self.assertEqual(response.context['form_title'], "Demographics-updated")
        self.client.logout()

        logged_in = self.client.login(username='admin', password='admin')
        self.assertTrue(logged_in)
        response = self.client.get(
            reverse(
                'patient_edit',
                kwargs={'registry_code': self.registry.code, "patient_id": patient.id}
            )
        )
        self.assertEqual(response.context['form_title'], "Demographics")
