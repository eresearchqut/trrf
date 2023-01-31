import datetime
import itertools
import logging
import operator
from functools import reduce

from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict

from rdrf.events.events import EventType
from rdrf.models.definition.models import LongitudinalFollowup
from rdrf.services.io.notifications.email_notification import process_notification
from registry.patients.models import LongitudinalFollowupEntry, LongitudinalFollowupQueueState

logger = logging.getLogger(__name__)


def handle_longitudinal_followups(user, patient, context_form_group):
    now = datetime.datetime.now()
    longitudinal_followups = LongitudinalFollowup.objects.filter(context_form_group=context_form_group)
    LongitudinalFollowupEntry.objects.bulk_create([
        LongitudinalFollowupEntry(
            longitudinal_followup=longitudinal_followup,
            patient=patient,
            state=LongitudinalFollowupQueueState.PENDING,
            send_at=now + longitudinal_followup.frequency,
            created_by=user,
        )
        for longitudinal_followup in longitudinal_followups
    ])


def evaluate_condition(longitudinal_followup_entry):
    if condition := longitudinal_followup_entry.longitudinal_followup.condition:
        return eval(condition, {'patient': longitudinal_followup_entry.patient})
    else:
        return True


def serialize_entries(patient_entries):
    grouped = itertools.groupby(
        [
            {
                "entry": {
                    "created_at": entry.created_at.timestamp(),
                    "created_by": entry.created_by,
                },
                "longitudinal_followup": {
                    "name": entry.longitudinal_followup.name,
                    "description": entry.longitudinal_followup.description,
                    "context_form_group": {
                        "name": entry.longitudinal_followup.context_form_group.name,
                        "context_type": entry.longitudinal_followup.context_form_group.context_type,
                        "forms": [
                            model_to_dict(
                                item.registry_form,
                                fields=["name", "abbreviated_name", "display_name", "tags"]
                            )
                            for item in entry.longitudinal_followup.context_form_group.items.all()
                        ]
                    },
                }
            }
            for entry in patient_entries
        ],
        lambda lfe: lfe["longitudinal_followup"]["name"]
    )

    return {longitudinal_followup: list(entries) for longitudinal_followup, entries in grouped}

def with_now(func):
    def wrapper(now=None):
        return func(now=now or datetime.datetime.now())
    return wrapper

@with_now
def send_longitudinal_followups(now):
    longitudinal_followups = LongitudinalFollowupEntry.objects.filter(
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
    ) \
        .select_related("longitudinal_followup") \
        .select_related("longitudinal_followup__context_form_group") \
        .select_related("patient") \
        .order_by("patient__id")

    for patient_id, patient_entries_group in itertools.groupby(longitudinal_followups, lambda e: e.patient.id):
        all_patient_entries = list(patient_entries_group)
        patient_entries = list(filter(evaluate_condition, all_patient_entries))
        logger.info(f"Patient {patient_id}: {len(patient_entries)} / {len(all_patient_entries)} followup entries")

        if len(patient_entries) == 0:
            continue

        patient = patient_entries[0].patient

        # At least one email that's eligible before debounce
        assert any(entry.send_at <= now for entry in patient_entries)

        now = datetime.datetime.now()

        longitudinal_followups = serialize_entries(patient_entries)
        try:
            process_notification(
                patient.rdrf_registry.first().code,
                EventType.LONGITUDINAL_FOLLOWUP, {
                    "patient": patient,
                    "longitudinal_followups": longitudinal_followups,
                }
            )
        except Exception as e:
            logger.error(e)

        for entry in patient_entries:
            entry.sent_at.append(now)
            entry.state = LongitudinalFollowupQueueState.SENT

        LongitudinalFollowupEntry.objects.bulk_update(patient_entries, ["sent_at", "state"])
