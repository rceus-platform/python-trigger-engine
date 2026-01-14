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


def extract_audio_for_gemini(video_path: Path) -> Path:
    ffmpeg = get_ffmpeg_path()

    audio_path = video_path.with_suffix(".wav")

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-t",
        "60",
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
