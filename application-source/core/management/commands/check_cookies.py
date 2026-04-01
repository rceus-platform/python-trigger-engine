"""Management command: check Instagram cookie health and alert admins.

Usage:
    python manage.py check_cookies          # check + email if bad
    python manage.py check_cookies --quiet  # exit code only (for cron)
"""

from django.core.management.base import BaseCommand

from core.services.cookie_health import check_cookie_file, send_cookie_alert


class Command(BaseCommand):
    help = "Check Instagram cookie health and optionally alert admins."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress output; use exit code (0 = ok, 1 = bad).",
        )
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Skip sending the alert email.",
        )

    def handle(self, *args, **options):
        report = check_cookie_file()

        if not options["quiet"]:
            status = self.style.SUCCESS("✓ OK") if report["ok"] else self.style.ERROR("✗ FAIL")
            self.stdout.write(f"{status}  {report['message']}")

        if not report["ok"] and not options["no_email"]:
            send_cookie_alert(report)
            if not options["quiet"]:
                self.stdout.write(self.style.WARNING("Alert email sent to admins."))

        # Exit code for scripting / cron
        if not report["ok"]:
            raise SystemExit(1)
