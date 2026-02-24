"""Helpers for composing and attaching email artifacts."""

import logging
import os
from mimetypes import guess_type

from django.core.mail import EmailMultiAlternatives

from core.constants import DAILY_RECALL_EMAILS, EMAIL_HOST_USER

logger = logging.getLogger(__name__)
MAX_EMAIL_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 MB


def build_daily_email(subject: str, body: str) -> EmailMultiAlternatives:
    """Construct the base daily email sent to the recall list."""

    return EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=EMAIL_HOST_USER,
        to=DAILY_RECALL_EMAILS,
    )


def attach_audio_if_small(email, audio_path: str | None) -> bool:
    """
    Attaches audio file to email if size allows.
    Returns True if attached, False otherwise.
    """
    logger.debug("attach_audio_if_small called with: %s", audio_path)

    if not audio_path:
        logger.debug("audio_path is None or empty")
        return False

    if not os.path.exists(audio_path):
        logger.warning("Audio file does not exist: %s", audio_path)
        return False

    logger.debug("Audio file exists: %s", audio_path)

    size = os.path.getsize(audio_path)
    logger.debug("Audio file size: %s bytes", size)
    if size > MAX_EMAIL_ATTACHMENT_SIZE:
        logger.warning(
            "Audio file too large: %s > %s",
            size,
            MAX_EMAIL_ATTACHMENT_SIZE,
        )
        return False

    try:
        mime_type, _ = guess_type(audio_path)
        mime_type = mime_type or "application/octet-stream"

        with open(audio_path, "rb") as f:
            content = f.read()
            logger.debug("Read %s bytes from audio file", len(content))
            email.attach(
                filename=os.path.basename(audio_path),
                content=content,
                mimetype=mime_type,
            )
        logger.info(
            "Successfully attached audio: %s",
            os.path.basename(audio_path),
        )
        return True
    except (IOError, OSError) as e:
        # File was deleted or inaccessible
        logger.error("Failed to attach audio: %s", e)
        return False
