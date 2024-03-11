from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from rdrf.models.definition.models import LongitudinalFollowup, Registry, RDRFContext, ClinicalData, ConsentQuestion
from registry.patients.models import Patient, LongitudinalFollowupEntry, LongitudinalFollowupQueueState, LivingStates


class Command(BaseCommand):
    help = "Create pending longitudinal followup entries for patients in a registry"

    def add_arguments(self, parser):
        parser.add_argument("registry_code", type=str)
        parser.add_argument("longitudinal_followup_name", type=str)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--allow-duplicates", action="store_true")
        parser.add_argument("--check-for-form-response", action="store_true")
        parser.add_argument("--require-consents", type=str, nargs="+", default=[])
        parser.add_argument("--allowed-patients", type=int, nargs="+", default=[])
        parser.add_argument("--created-before", type=int, default=None)
        parser.add_argument("--require-living", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        registry_code = options["registry_code"]
        longitudinal_followup_name = options["longitudinal_followup_name"]
        limit = options["limit"]
        allow_duplicates = options["allow_duplicates"]
        check_for_form_response = options["check_for_form_response"]
        require_consents = options["require_consents"]
        allowed_patients = set(options["allowed_patients"])
        created_before = datetime.utcfromtimestamp(options["created_before"]) if options["created_before"] else None
        require_living = options["require_living"]
        dry_run = options["dry_run"]

        try:
            registry = Registry.objects.get(code=registry_code)
            longitudinal_followup = LongitudinalFollowup.objects.get(name=longitudinal_followup_name)
        except Registry.DoesNotExist:
            raise CommandError(f"Registry {registry_code} does not exist")
        except LongitudinalFollowup.DoesNotExist:
            raise CommandError(f"LongitudinalFollowup {longitudinal_followup_name} does not exist")

        consent_questions = []
        for consent_question in require_consents:
            try:
                consent_questions.append(ConsentQuestion.objects.get(code=consent_question))
            except ConsentQuestion.DoesNotExist:
                raise CommandError(f"ConsentQuestion {consent_question} does not exist")

        pending_entries = LongitudinalFollowupEntry.objects.filter(
            longitudinal_followup=longitudinal_followup,
            state=LongitudinalFollowupQueueState.PENDING
        )
        self.stdout.write(self.style.SUCCESS(f"Found {len(pending_entries)} pending entries"))

        now = datetime.now()
        patients = Patient.objects.filter(rdrf_registry=registry)

        def can_add(patient):
            if allowed_patients and patient.id not in allowed_patients:
                return False

            if created_before and patient.created_at > created_before:
                return False

            if not allow_duplicates and pending_entries.filter(patient=patient).exists():
                return False

            if check_for_form_response:
                contexts = RDRFContext.objects.get_for_patient(patient, registry).filter(
                    context_form_group=longitudinal_followup.context_form_group)

                if not contexts.exists():
                    return False

                for context in contexts:
                    context_response = ClinicalData.objects.filter(
                        django_id=patient.id,
                        context_id=context.id,
                        collection="cdes"
                    ).first()

                    if not context_response:
                        return False

                    if context_response.last_updated_at + longitudinal_followup.frequency > now:
                        return False

            if require_consents:
                for consent in consent_questions:
                    if not patient.get_consent(consent):
                        return False

            if require_living:
                if patient.living_status != LivingStates.ALIVE:
                    return False

            return True

        new_entries = [
            LongitudinalFollowupEntry(
                longitudinal_followup=longitudinal_followup,
                patient=patient,
                state=LongitudinalFollowupQueueState.PENDING,
                send_at=now,
            )
            for patient in patients if can_add(patient)
        ]

        limited_entries = new_entries[:limit]

        input(f"Creating {len(limited_entries)} entries from {len(new_entries)} possible. Press enter to continue")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would create {len(limited_entries)} entries"))
        else:
            LongitudinalFollowupEntry.objects.bulk_create(limited_entries)
            self.stdout.write(self.style.SUCCESS(f"Created {len(limited_entries)} entries"))
