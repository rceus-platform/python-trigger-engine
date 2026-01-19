import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import ReelInsight
from core.services.email_new_reel import send_new_reel_email

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReelInsight)
def send_email_on_new_reel(sender, instance, created, **kwargs):
    if not created:
        return

    audio_path = getattr(instance, "_audio_path", None)
    logger.info(f"Signal handler: audio_path = {audio_path}")

    try:
        send_new_reel_email(instance, audio_path=audio_path)
    except Exception as e:
        logger.error(f"New reel email failed: {e}", exc_info=True)
