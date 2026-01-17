from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.constants import DAILY_RECALL_EMAILS, EMAIL_HOST_USER


def send_new_reel_email(insight):
    subject = "TRIGGER ENGINE: New Reel Processed"

    triggers = insight.triggers.splitlines()

    text_body = "\n".join(
        [
            "A new reel was processed.",
            "",
            "Triggers:",
            *[f"- {t}" for t in triggers],
        ]
    )

    html_body = render_to_string(
        "emails/reel_processed.html",
        {
            "insight": insight,
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
