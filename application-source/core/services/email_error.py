"""Email alerts for system failures."""

import logging

from django.core.mail import EmailMessage

from core.constants import ADMIN_EMAILS, EMAIL_HOST_USER

logger = logging.getLogger(__name__)


def send_error_email(url: str, error_message: str, traceback_text: str):
    """Notify administrators about a processing failure."""

    subject = f"TRIGGER ENGINE ERROR: {url[:30]}..."
    
    body = f"""
Trigger Engine encountered an error while processing:
URL: {url}

ERROR:
{error_message}

TRACEBACK:
{traceback_text}
"""

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=EMAIL_HOST_USER,
            to=ADMIN_EMAILS,
        )
        email.send(fail_silently=False)
        logger.info("Error email sent to admins for URL: %s", url)
    except Exception:
        logger.exception("Failed to send error email")
