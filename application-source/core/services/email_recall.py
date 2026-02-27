"""Send daily recall emails to the configured distribution list."""

from django.template.loader import render_to_string
from django.utils import timezone

from core.services.email_utils import build_daily_email
from core.services.recall import get_daily_triggers


def send_daily_recall_email():
    """Send the daily recall email, returning True when something was sent."""
    triggers = get_daily_triggers(limit=5)

    if not triggers:
        return False

    today = timezone.localdate().isoformat()
    subject = f"Daily Recall — {today}"

    text_body = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(triggers)])

    html_body = render_to_string(
        "emails/daily_recall.html",
        {
            "date": today,
            "triggers": triggers,
        },
    )

    email = build_daily_email(subject, text_body)

    email.attach_alternative(html_body, "text/html")
    email.send()

    return True
