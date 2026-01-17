from datetime import date

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.constants import DAILY_RECALL_EMAILS, EMAIL_HOST_USER
from core.services.recall import get_daily_triggers


def send_daily_recall_email():
    triggers = get_daily_triggers(limit=5)

    if not triggers:
        return False

    today = date.today().isoformat()
    subject = f"Daily Recall — {today}"

    text_body = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(triggers)])

    html_body = render_to_string(
        "emails/daily_recall.html",
        {
            "date": today,
            "triggers": triggers,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=EMAIL_HOST_USER,
        to=DAILY_RECALL_EMAILS,
    )

    email.attach_alternative(html_body, "text/html")
    email.send()

    return True
