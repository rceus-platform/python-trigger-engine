import platform
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def get_ffmpeg_path() -> Path:
    system = platform.system()

    if system == "Windows":
        ffmpeg_path = BASE_DIR / "tools" / "windows" / "ffmpeg.exe"
    elif system == "Linux":
        ffmpeg_path = BASE_DIR / "tools" / "linux" / "ffmpeg"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    if not ffmpeg_path.exists():
        raise RuntimeError(f"ffmpeg binary not found at: {ffmpeg_path}")

    return ffmpeg_path
