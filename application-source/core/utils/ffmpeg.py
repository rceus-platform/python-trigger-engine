import shutil


def get_ffmpeg_path():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and ensure it is in PATH."
        )
    return ffmpeg
