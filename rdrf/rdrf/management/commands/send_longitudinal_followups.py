from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from rdrf.services.io.notifications.longitudinal_followups import (
    send_longitudinal_followups,
)


class Command(BaseCommand):
    help = "Send longitudinal followup emails"

    def add_arguments(self, parser):
        parser.add_argument("delta_seconds", type=int)

    def handle(self, *args, **options):
        delta_seconds = options["delta_seconds"]

        now = timezone.now()
        send_longitudinal_followups(now + timedelta(seconds=delta_seconds))
