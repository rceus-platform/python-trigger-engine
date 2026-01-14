import subprocess
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


def download_reel(url: str) -> Path:
    """
    Downloads an Instagram reel and returns the video file path.
    """
    output_template = MEDIA_DIR / "%(id)s.%(ext)s"

    command = [
        "yt-dlp",
        "-f",
        "mp4",
        "-o",
        str(output_template),
        url,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    # Find the downloaded file
    files = list(MEDIA_DIR.glob("*.mp4"))
    if not files:
        raise RuntimeError("Video download failed")

    return files[-1]
