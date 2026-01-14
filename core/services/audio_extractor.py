import subprocess
from pathlib import Path

from core.utils.ffmpeg import get_ffmpeg_path


def extract_audio(video_path: Path) -> Path:
    print(">>> AUDIO EXTRACTION STARTED FOR:", video_path)

    ffmpeg = get_ffmpeg_path()
    video_path = Path(video_path).resolve()
    audio_path = video_path.with_suffix(".mp3")

    command = [
        str(ffmpeg),
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-af",
        "loudnorm",
        "-t",
        "45",
        str(audio_path),
    ]

    subprocess.run(command, check=True)
    print(">>> AUDIO EXTRACTED AT:", audio_path)

    if not audio_path.exists():
        raise RuntimeError("Audio extraction failed")

    return audio_path


def extract_audio_for_gemini(video_path: Path) -> Path:
    ffmpeg = get_ffmpeg_path()
    audio_path = video_path.with_suffix(".wav")

    command = [
        str(ffmpeg),
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
        audio_path,
    ]

    subprocess.run(command, check=True)
    return audio_path
