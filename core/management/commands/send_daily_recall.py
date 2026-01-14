from django.core.management.base import BaseCommand

from core.services.email_recall import send_daily_recall_email


class Command(BaseCommand):
    help = "Send daily recall email"

    def handle(self, *args, **options):
        success = send_daily_recall_email()

        if success:
            self.stdout.write(self.style.SUCCESS("Daily recall email sent"))
        else:
            self.stdout.write(self.style.WARNING("No triggers to send"))
