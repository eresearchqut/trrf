import json
import logging
from datetime import timedelta, datetime

from django.core import mail
from django.test import TestCase

from rdrf.events.events import EventType
from rdrf.models.definition.models import Registry, ContextFormGroup, LongitudinalFollowup, EmailNotification, \
    EmailTemplate, RegistryForm, ContextFormGroupItem, Section, CommonDataElement, ConsentSection, ConsentQuestion
from rdrf.services.io.notifications.longitudinal_followups import send_longitudinal_followups, ConditionException
from registry.patients.models import LongitudinalFollowupEntry, Patient, LongitudinalFollowupQueueState, ConsentValue

logger = logging.getLogger(__name__)


class LongitudinalFollowupSetupMixin:
    def create_models(self):
        self.now = datetime.now()
        self.registry = Registry.objects.create(
            code='reg',
            metadata_json=json.dumps({'features': ['longitudinal_followups']})
        )

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
            code="test",
            abbreviated_name="test",
            name="test"
        )
        Section.objects.create(
            code="test",
            elements="test",
            abbreviated_name="test",
            display_name="test"
        )
        form = RegistryForm.objects.create(
            registry=self.registry,
            name="test",
            abbreviated_name="test",
            sections="test"
        )

        self.cfg = ContextFormGroup.objects.create(registry=self.registry, code='cfg')
        cfg_item = ContextFormGroupItem.objects.create(context_form_group=self.cfg, registry_form=form)
        self.cfg.items.add(cfg_item)

    def get_emails(self, num_emails):
        self.assertEqual(len(mail.outbox), 0)
        send_longitudinal_followups(self.now)
        self.assertEqual(len(mail.outbox), num_emails)
        return mail.outbox


class LongitudinalFollowupSentTest(TestCase, LongitudinalFollowupSetupMixin):
    def setUp(self):
        self.create_models()

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
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
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

        email = self.get_emails(1)[0]
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
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
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
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=52, days=1)
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

        email = self.get_emails(1)[0]

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
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
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
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
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

        [email1, email2] = self.get_emails(2)

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

    def test_multiple_patient_multiple_lf(self):
        longitudinal_followup1 = LongitudinalFollowup.objects.create(
            name="Test followup 1",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=26),
            debounce=timedelta(weeks=26)
        )
        longitudinal_followup2 = LongitudinalFollowup.objects.create(
            name="Test followup 2",
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
                longitudinal_followup=longitudinal_followup1,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient1,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient1,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup1,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient2,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=26, days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now - timedelta(days=1)
            ),
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup2,
                patient=patient2,
                state=LongitudinalFollowupQueueState.SENT,
                send_at=self.now + timedelta(days=1)
            )
        ])

        emails = self.get_emails(2)

        for email in emails:
            body = json.loads(email.body)
            logger.debug(body)
            for lf in ["Test followup 1", "Test followup 2"]:
                entries = body.get(lf)
                self.assertIsNotNone(entries)
                self.assertEqual(len(entries), 2)


class LongitudinalFollowupConditionTest(TestCase, LongitudinalFollowupSetupMixin):
    def setUp(self):
        self.create_models()

    def create_entry(self, condition):
        longitudinal_followup = LongitudinalFollowup.objects.create(
            name="Test followup",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=1),
            debounce=timedelta(weeks=1),
            condition=condition
        )

        consent_section = ConsentSection.objects.create(
            code="test",
            section_label="Test",
            registry=self.registry,
        )
        question1 = ConsentQuestion.objects.create(
            code="test1",
            section=consent_section,
        )
        question2 = ConsentQuestion.objects.create(
            code="test2",
            section=consent_section,
        )

        patient = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient.rdrf_registry.add(self.registry)
        patient.save()

        ConsentValue.objects.create(
            patient=patient,
            consent_question=question1,
            answer=True
        )
        ConsentValue.objects.create(
            patient=patient,
            consent_question=question2,
            answer=False
        )

        LongitudinalFollowupEntry.objects.create(
            longitudinal_followup=longitudinal_followup,
            patient=patient,
            state=LongitudinalFollowupQueueState.PENDING,
            send_at=self.now - timedelta(days=1)
        )

    def test_true(self):
        self.create_entry("patient.date_of_birth.year == 1970")
        self.get_emails(1)

    def test_false(self):
        self.create_entry("patient.date_of_birth.year == 1971")
        self.get_emails(0)

    def test_exception(self):
        self.create_entry("patient.missing_property")
        with self.assertRaises(ConditionException):
            self.get_emails(0)

    def test_consent_true(self):
        self.create_entry("consents.get('reg.test.test1') == True")
        self.get_emails(1)

    def test_consent_false(self):
        self.create_entry("consents.get('reg.test.test2') == True")
        self.get_emails(0)

    def test_consent_none(self):
        self.create_entry("consents.get('reg.test.test3') == True")
        self.get_emails(0)


class LongitudinalFollowupDebounceTest(TestCase, LongitudinalFollowupSetupMixin):
    def setUp(self):
        self.create_models()

    def create_patient_and_followup(self, frequency_weeks, debounce_weeks):
        longitudinal_followup = LongitudinalFollowup.objects.create(
            name="Test followup",
            context_form_group=self.cfg,
            frequency=timedelta(weeks=frequency_weeks),
            debounce=timedelta(weeks=debounce_weeks)
        )
        patient = Patient.objects.create(consent=True, date_of_birth=datetime(1970, 1, 1), sex="3")
        patient.rdrf_registry.add(self.registry)
        patient.save()
        return patient, longitudinal_followup

    def create_entries(self, patient, longitudinal_followup, send_at_deltas):
        LongitudinalFollowupEntry.objects.bulk_create([
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=self.now + timedelta(weeks=delta)
            ) for delta in send_at_deltas
        ])

    def test_none(self):
        self.create_patient_and_followup(26, 0)
        self.get_emails(0)

    def test_now(self):
        patient, followup = self.create_patient_and_followup(26, 0)
        self.create_entries(patient, followup, [0])
        self.get_emails(1)

    def test_1_before(self):
        patient, followup = self.create_patient_and_followup(26, 0)
        self.create_entries(patient, followup, [-1])
        self.get_emails(1)

    def test_1_after(self):
        patient, followup = self.create_patient_and_followup(26, 0)
        self.create_entries(patient, followup, [1])
        self.get_emails(0)

    def test_1_before_1_after(self):
        patient, followup = self.create_patient_and_followup(26, 0)
        self.create_entries(patient, followup, [-1, 1])
        self.get_emails(1)

    def test_1_before_debounced(self):
        patient, followup = self.create_patient_and_followup(26, 13)
        self.create_entries(patient, followup, [-1])
        self.get_emails(1)

    def test_1_after_debounced(self):
        patient, followup = self.create_patient_and_followup(26, 13)
        self.create_entries(patient, followup, [1])
        self.get_emails(0)

    def test_1_before_1_after_debounced(self):
        patient, followup = self.create_patient_and_followup(26, 13)
        self.create_entries(patient, followup, [-1, 1])
        email = self.get_emails(1)[0]
        body = json.loads(email.body)
        self.assertEqual(len(body.get("Test followup")), 2)

    def test_1_before_1_after_not_debounced(self):
        patient, followup = self.create_patient_and_followup(26, 13)
        self.create_entries(patient, followup, [-1, 14])
        email = self.get_emails(1)[0]
        body = json.loads(email.body)
        self.assertEqual(len(body.get("Test followup")), 1)
