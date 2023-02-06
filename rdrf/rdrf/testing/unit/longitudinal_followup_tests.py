import json
import logging
import textwrap
from datetime import timedelta, datetime

from django.core import mail
from django.test import TestCase

from rdrf.events.events import EventType
from rdrf.models.definition.models import Registry, ContextFormGroup, LongitudinalFollowup, EmailNotification, \
    EmailTemplate, RegistryForm, ContextFormGroupItem, Section, CommonDataElement
from rdrf.services.io.notifications.longitudinal_followups import send_longitudinal_followups
from registry.patients.models import LongitudinalFollowupEntry, Patient, LongitudinalFollowupQueueState

logger = logging.getLogger(__name__)


class LongitudinalFollowupSentTest(TestCase):
    def setUp(self):
        self.now = datetime.now()
        self.registry = Registry.objects.create(code='reg')

        template = EmailTemplate.objects.create(
            language='en',
            description='Longitudinal Followup',
            subject='Longitudinal Followup',
            body="{{ longitudinal_followups | json_script:'' | striptags }}",
        )
        email_notification = EmailNotification.objects.create(
            registry=self.registry,
            description=EventType.LONGITUDINAL_FOLLOWUP,
            email_from="example@example.example",
            recipient="example@example.example",
        )
        email_notification.email_templates.add(template)
        email_notification.save()

        CommonDataElement.objects.create(
            code=f'test',
            abbreviated_name=f'test',
            name="test"
        )
        Section.objects.create(
            code=f'test',
            elements=f'test',
            abbreviated_name=f'test',
            display_name=f'test'
        )
        form = RegistryForm.objects.create(
            registry=self.registry,
            name=f'test',
            abbreviated_name=f'test',
            sections=f'test'
        )

        self.cfg = ContextFormGroup.objects.create(registry=self.registry, code='cfg')
        cfg_item = ContextFormGroupItem.objects.create(context_form_group=self.cfg, registry_form=form)
        self.cfg.items.add(cfg_item)

    def _get_emails(self, num_emails):
        self.assertEqual(len(mail.outbox), 0)
        send_longitudinal_followups(self.now)
        self.assertEqual(len(mail.outbox), num_emails)
        return mail.outbox

    def test_single_patient_single_lf(self):
        longitudinal_followup = LongitudinalFollowup.objects.create(
            name="Test followup",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=26),
            debounce=timedelta(weeks=26)
        )
        patient = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient.rdrf_registry.add(self.registry)

        LongitudinalFollowupEntry.objects.bulk_create([
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
        ])

        email = self._get_emails(1)[0]
        self.assertEqual(email.subject, "Longitudinal Followup")

        body = json.loads(email.body)
        logger.debug(body)
        entries = body.get("Test followup")
        self.assertIsNotNone(entries)
        self.assertEqual(len(entries), 2)

    def test_single_patient_multiple_lf(self):
        longitudinal_followup1 = LongitudinalFollowup.objects.create(
            name="Test followup 1",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=26),
            debounce=timedelta(weeks=26)
        )
        longitudinal_followup2 = LongitudinalFollowup.objects.create(
            name="Test followup 2",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=52),
            debounce=timedelta(weeks=52)
        )
        patient = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient.rdrf_registry.add(self.registry)

        LongitudinalFollowupEntry.objects.bulk_create([
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
        ])

        email = self._get_emails(1)[0]

        body = json.loads(email.body)
        logger.debug(body)
        first_entries = body.get("Test followup 1")
        self.assertIsNotNone(first_entries)
        self.assertEqual(len(first_entries), 2)
        second_entries = body.get("Test followup 2")
        self.assertIsNotNone(second_entries)
        self.assertEqual(len(second_entries), 2)

    def test_multiple_patient_single_lf(self):
        longitudinal_followup = LongitudinalFollowup.objects.create(
            name="Test followup",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=26),
            debounce=timedelta(weeks=26)
        )
        patient1 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient1.rdrf_registry.add(self.registry)

        patient2 = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient2.rdrf_registry.add(self.registry)

        LongitudinalFollowupEntry.objects.bulk_create([
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
        ])

        [email1, email2] = self._get_emails(2)

        body = json.loads(email1.body)
        logger.debug(body)
        entries = body.get("Test followup")
        self.assertIsNotNone(entries)
        self.assertEqual(len(entries), 2)

        body = json.loads(email2.body)
        logger.debug(body)
        entries = body.get("Test followup")
        self.assertIsNotNone(entries)
        self.assertEqual(len(entries), 2)
