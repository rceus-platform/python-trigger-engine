"""Signal handlers for the core app."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import ReelInsight
from core.services.email_new_reel import send_new_reel_email

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReelInsight)
def send_email_on_new_reel(sender, instance, created, **_kwargs):
    """Send an email whenever a new ReelInsight is saved."""

    _ = sender

    if not created:
        return

    audio_path = getattr(instance, "audio_path_for_email", None)
    logger.info("Signal handler: audio_path = %s", audio_path)

    try:
        send_new_reel_email(instance, audio_path=audio_path)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("New reel email failed: %s", exc, exc_info=True)
