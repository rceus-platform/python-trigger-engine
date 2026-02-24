"""Management command for the daily recall email."""

from django.core.management.base import BaseCommand

from core.services.email_recall import send_daily_recall_email


class Command(BaseCommand):
    """Send the daily recall email to configured recipients."""

    help = "Send daily recall email"

    def handle(self, *args, **options):
        warning_style = getattr(self.style, "WARNING", lambda message: message)

        success = send_daily_recall_email()

        if success:
            self.stdout.write(self.style.SUCCESS("Daily recall email sent"))
        else:
            self.stdout.write(warning_style("No triggers to send"))
