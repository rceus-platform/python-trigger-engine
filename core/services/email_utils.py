import logging
import os
from mimetypes import guess_type

logger = logging.getLogger(__name__)
MAX_EMAIL_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 MB


def attach_audio_if_small(email, audio_path: str) -> bool:
    """
    Attaches audio file to email if size allows.
    Returns True if attached, False otherwise.
    """
    logger.debug(f"attach_audio_if_small called with: {audio_path}")

    if not audio_path:
        logger.debug("audio_path is None or empty")
        return False

    if not os.path.exists(audio_path):
        logger.warning(f"Audio file does not exist: {audio_path}")
        return False

    logger.debug(f"Audio file exists: {audio_path}")

    size = os.path.getsize(audio_path)
    logger.debug(f"Audio file size: {size} bytes")
    if size > MAX_EMAIL_ATTACHMENT_SIZE:
        logger.warning(f"Audio file too large: {size} > {MAX_EMAIL_ATTACHMENT_SIZE}")
        return False

    try:
        mime_type, _ = guess_type(audio_path)
        mime_type = mime_type or "application/octet-stream"

        with open(audio_path, "rb") as f:
            content = f.read()
            logger.debug(f"Read {len(content)} bytes from audio file")
            email.attach(
                filename=os.path.basename(audio_path),
                content=content,
                mimetype=mime_type,
            )
        logger.info(f"Successfully attached audio: {os.path.basename(audio_path)}")
        return True
    except (IOError, OSError) as e:
        # File was deleted or inaccessible
        logger.error(f"Failed to attach audio: {e}")
        return False
