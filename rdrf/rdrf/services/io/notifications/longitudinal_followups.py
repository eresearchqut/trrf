import datetime
import itertools
import logging
from urllib.parse import urlencode

from django.db.models import F, Value, ExpressionWrapper, DateTimeField, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.urls import reverse

from rdrf.events.events import EventType
from rdrf.helpers.registry_features import RegistryFeatures
from rdrf.models.definition.models import LongitudinalFollowup, ContextFormGroupItem, Registry
from rdrf.services.io.notifications.email_notification import process_notification
from registry.patients.models import LongitudinalFollowupEntry, LongitudinalFollowupQueueState, ConsentValue

logger = logging.getLogger(__name__)


def handle_longitudinal_followups(user, patient, registry, context_form_group):
    if not registry.has_feature(RegistryFeatures.LONGITUDINAL_FOLLOWUPS):
        return

    if context_form_group is None:
        return

    now = datetime.datetime.now()
    new_entries = [
        LongitudinalFollowupEntry(
            longitudinal_followup=longitudinal_followup,
            patient=patient,
            state=LongitudinalFollowupQueueState.PENDING,
            send_at=now + longitudinal_followup.frequency, created_by=user,
        ) for longitudinal_followup in LongitudinalFollowup.objects.filter(context_form_group=context_form_group)
    ]
    logger.debug(f"Creating {len(new_entries)} longitudinal followup entries {patient.id=} {context_form_group.id=}")
    created_entries = LongitudinalFollowupEntry.objects.bulk_create(new_entries)
    logger.info(f"Created {len(created_entries)} longitudinal followup entries")


# Custom ConditionException that wraps the original exception
class ConditionException(Exception):
    def __init__(self, original_exception):
        self.original_exception = original_exception

    def __str__(self):
        return f"ConditionException: {self.original_exception}"


def _get_consents(patient):
    return {
        f"{registry.code}.{section.code}.{question.code}": (
            consent_value.answer
            if (consent_value := ConsentValue.objects.filter(patient=patient, consent_question=question).first())
            else None
        )
        for registry in patient.rdrf_registry.all()
        for section in registry.consent_sections.all()
        for question in section.questions.all()
    }


def evaluate_condition(longitudinal_followup_entry):
    if condition := longitudinal_followup_entry.longitudinal_followup.condition:
        try:
            patient = longitudinal_followup_entry.patient
            return eval(
                condition,
                {
                    'patient': patient.as_dto(),
                    'consents': _get_consents(patient),
                }
            )
        except Exception as e:
            logger.error(f"Error evaluating condition {condition} for {longitudinal_followup_entry.id=}")
            raise ConditionException(e)
    else:
        return True


def form_link_query(longitudinal_followup_entry):
    return {
        'action': 'form',
        'form_type': 'Registry',
        'registry': longitudinal_followup_entry.registry_code,
        'id': longitudinal_followup_entry.patient_id,
        'cfg': longitudinal_followup_entry.context_form_group_name,
        'form': longitudinal_followup_entry.first_form_name
    }


def serialize_entries(patient_entries):
    grouped = itertools.groupby(
        [
            {
                "entry": {
                    "created_at": entry.created_at.timestamp(),
                },
                "longitudinal_followup": {
                    "name": entry.longitudinal_followup_name,
                    "description": entry.longitudinal_followup_description,
                    "context_form_group": {
                        "name": entry.context_form_group_name,
                        "context_type": entry.context_form_group_context_type,
                        "link": f"{reverse('action')}?{urlencode(form_link_query(entry))}",
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
    allowed_registries = [
        r.code for r in Registry.objects.all() if r.has_feature(RegistryFeatures.LONGITUDINAL_FOLLOWUPS)
    ]

    outstanding_entries = LongitudinalFollowupEntry.objects.annotate(
        debounce_value=Coalesce(
            "longitudinal_followup__debounce",
            Value(datetime.timedelta(seconds=0))
        ),
        send_at_debounced=ExpressionWrapper(
            F("send_at") - F("debounce_value"),
            output_field=DateTimeField()
        ),
        first_form_name=Subquery(
            ContextFormGroupItem.objects.filter(
                context_form_group=OuterRef("longitudinal_followup__context_form_group__id")
            ).values("registry_form__name")[:1]
        ),
        longitudinal_followup_name=F("longitudinal_followup__name"),
        longitudinal_followup_description=F("longitudinal_followup__description"),
        context_form_group_name=F("longitudinal_followup__context_form_group__name"),
        context_form_group_context_type=F("longitudinal_followup__context_form_group__context_type"),
        registry_code=F("longitudinal_followup__context_form_group__registry__code"),
    ).filter(
        registry_code__in=allowed_registries,
        send_at_debounced__lte=now,
        state=LongitudinalFollowupQueueState.PENDING,
        patient__id__in=LongitudinalFollowupEntry.objects.filter(
            state=LongitudinalFollowupQueueState.PENDING,
            send_at__lte=now
        ).values("patient__id").distinct(),
    ).order_by("patient__id", "created_at")

    logger.info(f"Found {len(outstanding_entries)} outstanding followup entries")

    sent_success = sent_failure = 0
    for patient_id, patient_entries_group in itertools.groupby(outstanding_entries, lambda entry: entry.patient.id):
        all_patient_entries = list(patient_entries_group)
        patient_entries = list(filter(evaluate_condition, all_patient_entries))
        logger.debug(f"Patient {patient_id}: {len(patient_entries)} / {len(all_patient_entries)} followup entries")

        if len(patient_entries) == 0:
            continue

        patient = patient_entries[0].patient

        patient_registry = patient.rdrf_registry.first()

        if not patient_registry.has_feature(RegistryFeatures.LONGITUDINAL_FOLLOWUPS):
            logger.info(f"Halting longitudinal followup processing as registry {patient_registry.code} disabled the feature")
            break

        # At least one email that's eligible before debounce
        assert any(entry.send_at <= now for entry in patient_entries)

        sent_at = datetime.datetime.now()

        longitudinal_followups = serialize_entries(patient_entries)

        for entry in patient_entries:
            entry.sent_at.append(sent_at)
            entry.state = LongitudinalFollowupQueueState.SENT
        LongitudinalFollowupEntry.objects.bulk_update(patient_entries, ["sent_at", "state"])

        try:
            process_notification(
                patient_registry.code,
                EventType.LONGITUDINAL_FOLLOWUP, {
                    "patient": patient,
                    "longitudinal_followups": longitudinal_followups,
                }
            )
            sent_success += 1
        except Exception as e:
            logger.error(e)
            sent_failure += 1

    logger.info(f"Sent {sent_success} followup emails, failed to send {sent_failure}")
