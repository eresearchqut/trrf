import datetime
import itertools
import logging

from django.core import serializers
from django.db import transaction

from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import process_notification
from registry.patients.models import LongitudinalFollowupEntry

logger = logging.getLogger(__name__)


def send_longitudinal_followups():
    entries = LongitudinalFollowupEntry.objects.filter(
        state=LongitudinalFollowupEntry.QueueState.PENDING,
        send_at__lte=datetime.datetime.now(),
    ).order_by("patient").iterator(chunk_size=100)

    for patient, entries in itertools.groupby(entries, lambda e: e.patient):
        entries = list(entries)
        now = datetime.datetime.now()
        with transaction.atomic():
            sent_successfully, has_disabled = process_notification(patient.rdrf_registry.first().code, EventType.LONGITUDINAL_FOLLOWUP, {
                "patient": patient,
                "entries": serializers.serialize("json", entries),
            })

            if sent_successfully:
                for entry in entries:
                    entry.sent_at.append(now)
                    entry.state = LongitudinalFollowupEntry.QueueState.SENT
                    # entry.save()
                    # logger.info(entry.__dict__)
                    # logger.info(str((sent_successfully, has_disabled)))
