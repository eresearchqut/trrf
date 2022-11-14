import datetime
import itertools
import json
import logging
import operator
from functools import reduce

from django.core import serializers
from django.db import transaction
from django.db.models import Q

from rdrf.events.events import EventType
from rdrf.models.definition.models import LongitudinalFollowup
from rdrf.services.io.notifications.email_notification import process_notification
from registry.patients.models import LongitudinalFollowupEntry, LongitudinalFollowupQueueState

logger = logging.getLogger(__name__)


def evaluate_condition(longitudinal_followup_entry):
    if longitudinal_followup_entry.longitudinal_followup.condition:
        return eval(longitudinal_followup_entry.longitudinal_followup.condition,
                    {'patient': longitudinal_followup_entry.patient})
    else:
        return True


def send_longitudinal_followups():
    now = datetime.datetime.now()
    entries = LongitudinalFollowupEntry.objects.filter(
        reduce(
            operator.or_,
            [Q(longitudinal_followup=lf) & Q(send_at__lte=now + lf.debounce) for lf in
             LongitudinalFollowup.objects.all()]
        ),
        state=LongitudinalFollowupQueueState.PENDING,
        patient__id__in=LongitudinalFollowupEntry.objects.filter(
            state=LongitudinalFollowupQueueState.PENDING,
            send_at__lte=now
        ).values("patient__id").distinct()
    ).order_by("patient__id")

    for patient_id, entries in itertools.groupby(entries, lambda e: e.patient.id):
        entries = list(filter(evaluate_condition, entries))

        if len(entries) == 0:
            continue

        patient = entries[0].patient

        # At least one email that's eligible before debounce
        assert any((entry.send_at <= now for entry in entries))

        now = datetime.datetime.now()
        with transaction.atomic():
            sent_successfully, has_disabled = process_notification(
                patient.rdrf_registry.first().code,
                EventType.LONGITUDINAL_FOLLOWUP, {
                    "patient": patient,
                    "entries": json.loads(serializers.serialize("json", entries)),
                }
            )

            if sent_successfully:
                for entry in entries:
                    entry.sent_at.append(now)
                    entry.state = LongitudinalFollowupQueueState.SENT
                    # entry.save()
                    # logger.info(entry.__dict__)
                    # logger.info(str((sent_successfully, has_disabled)))
