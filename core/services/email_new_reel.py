import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.constants import DAILY_RECALL_EMAILS, EMAIL_HOST_USER

from .email_utils import attach_audio_if_small

logger = logging.getLogger(__name__)


def send_new_reel_email(insight, audio_path: str | None = None):
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

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=EMAIL_HOST_USER,
        to=DAILY_RECALL_EMAILS,
    )

    logger.info(f"Attempting to attach audio from: {audio_path}")
    audio_attached = attach_audio_if_small(email, audio_path)
    logger.info(f"Audio attachment result: {audio_attached}")

    html_body = render_to_string(
        "emails/reel_processed.html",
        {
            "insight": insight,
            "triggers": triggers,
            "audio_attached": audio_attached,
        },
    )

    email.attach_alternative(html_body, "text/html")

    email.send()
