"""Email notifications for newly processed reels."""

import logging

from django.template.loader import render_to_string

from .email_utils import attach_audio_if_small, build_daily_email

logger = logging.getLogger(__name__)


def send_new_reel_email(insight, audio_path: str | None = None):
    """Notify subscribers when a new reel has been processed."""
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

    email = build_daily_email(subject, text_body)

    logger.info("Attempting to attach audio from: %s", audio_path)
    if audio_path:
        audio_attached = attach_audio_if_small(email, audio_path)
    else:
        audio_attached = False
    logger.info("Audio attachment result: %s", audio_attached)

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
