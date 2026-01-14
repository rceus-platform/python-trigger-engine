import os
from pathlib import Path

from core.utils.ffmpeg import get_ffmpeg_path

# ---- Cross-platform ffmpeg injection ----
ffmpeg_path = get_ffmpeg_path()
ffmpeg_dir = ffmpeg_path.parent

os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")
# ----------------------------------------

import whisper

MODEL = whisper.load_model("small")


def transcribe_audio(audio_path: Path) -> tuple[str, str]:
    audio_path = Path(audio_path).resolve()

    if not audio_path.exists():
        raise RuntimeError(f"Audio file not found: {audio_path}")

    result = MODEL.transcribe(
        str(audio_path),
        task="transcribe",
        temperature=0.0,  # deterministic
        beam_size=1,  # IMPORTANT
        best_of=1,  # IMPORTANT
        no_speech_threshold=0.6,
        logprob_threshold=-1.0,
        compression_ratio_threshold=2.4,
    )

    language = result.get("language")
    text = result.get("text", "").strip()

    if not text:
        raise RuntimeError("Empty transcript")

    if language not in ["en", "hi", "mr"]:
        raise RuntimeError(f"Unsupported language: {language}")

    return language, text
