from django.core.management import BaseCommand

from rdrf.services.io.notifications.longitudinal_followups import send_longitudinal_followups


class Command(BaseCommand):
    help = "Send longitudinal followup emails"

    def handle(self, *args, **options):
        send_longitudinal_followups()
