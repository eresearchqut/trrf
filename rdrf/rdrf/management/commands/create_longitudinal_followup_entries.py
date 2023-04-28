from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from rdrf.models.definition.models import LongitudinalFollowup, Registry, RDRFContext, ClinicalData
from registry.patients.models import Patient, LongitudinalFollowupEntry, LongitudinalFollowupQueueState


class Command(BaseCommand):
    help = "Create pending longitudinal followup entries for patients in a registry"

    def add_arguments(self, parser):
        parser.add_argument("registry_code", type=str)
        parser.add_argument("longitudinal_followup_name", type=str)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--allow-duplicates", action="store_true")
        parser.add_argument("--check-for-form-response", action="store_true")

    def handle(self, *args, **options):
        registry_code = options["registry_code"]
        longitudinal_followup_name = options["longitudinal_followup_name"]
        limit = options["limit"]
        allow_duplicates = options["allow_duplicates"]
        check_for_form_response = options["check_for_form_response"]

        try:
            registry = Registry.objects.get(code=registry_code)
            longitudinal_followup = LongitudinalFollowup.objects.get(name=longitudinal_followup_name)
        except Registry.DoesNotExist:
            raise CommandError(f"Registry {registry_code} does not exist")
        except LongitudinalFollowup.DoesNotExist:
            raise CommandError(f"LongitudinalFollowup {longitudinal_followup_name} does not exist")

        pending_entries = LongitudinalFollowupEntry.objects.filter(
            longitudinal_followup=longitudinal_followup,
            state=LongitudinalFollowupQueueState.PENDING
        )
        self.stdout.write(self.style.SUCCESS(f"Found {len(pending_entries)} pending entries"))

        now = datetime.now()
        patients = Patient.objects.filter(rdrf_registry=registry)

        def can_add(patient):
            if not allow_duplicates and pending_entries.filter(patient=patient).exists():
                return False

            if check_for_form_response:
                context = RDRFContext.objects.get_for_patient(patient, registry).filter(
                    context_form_group=longitudinal_followup.context_form_group).first()

                if not context:
                    return False

                context_response = ClinicalData.objects.filter(django_id=patient, context_id=context).exists()

                if not context_response:
                    return False

            return True

        entries = LongitudinalFollowupEntry.objects.bulk_create(
            [
                LongitudinalFollowupEntry(
                    longitudinal_followup=longitudinal_followup,
                    patient=patient,
                    state=LongitudinalFollowupQueueState.PENDING,
                    send_at=now,
                ) for patient in patients if can_add(patient)
            ][:limit]
        )

        self.stdout.write(self.style.SUCCESS(f"Created {len(entries)} entries"))
