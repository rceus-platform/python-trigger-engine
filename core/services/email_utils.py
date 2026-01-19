import os
from mimetypes import guess_type

MAX_EMAIL_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 MB


def attach_audio_if_small(email, audio_path: str) -> bool:
    """
    Attaches audio file to email if size allows.
    Returns True if attached, False otherwise.
    """

    if not audio_path or not os.path.exists(audio_path):
        return False

    size = os.path.getsize(audio_path)
    if size > MAX_EMAIL_ATTACHMENT_SIZE:
        return False

    mime_type, _ = guess_type(audio_path)
    mime_type = mime_type or "application/octet-stream"

    with open(audio_path, "rb") as f:
        email.attach(
            filename=os.path.basename(audio_path),
            content=f.read(),
            mimetype=mime_type,
        )

    return True
