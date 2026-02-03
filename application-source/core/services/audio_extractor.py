import shutil
import subprocess
from pathlib import Path


def get_ffmpeg_path() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found in PATH. Install ffmpeg and restart the server."
        )
    return ffmpeg


def extract_audio_for_gemini(video_path: Path, bitrate: str = "64k") -> Path:
    """
    Extract audio from video with compression.

    Args:
        video_path: Path to video file
        bitrate: Audio bitrate (default 64k = ~500KB per minute)
                Use '128k' for better quality, '192k' for high quality
    """
    ffmpeg = get_ffmpeg_path()

    audio_path = video_path.with_suffix(".mp3")  # MP3 format for compression

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",  # No video
        "-ac",
        "1",  # Mono
        "-ar",
        "16000",  # 16kHz sample rate
        "-b:a",
        bitrate,  # Audio bitrate for compression
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    return audio_path
