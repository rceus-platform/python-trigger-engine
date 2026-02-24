"""Helper to locate the ffmpeg executable."""

import shutil


def get_ffmpeg_path():
    """Return an ffmpeg path or raise if the binary is missing."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and ensure it is in PATH."
        )
    return ffmpeg
