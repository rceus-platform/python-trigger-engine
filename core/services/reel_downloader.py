import logging
import subprocess
from pathlib import Path

from core.constants import DEBUG, INSTAGRAM_COOKIES_PATH

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


def download_reel(url: str) -> Path:
    """
    Downloads an Instagram reel and returns the video file path.
    """

    logger.info("Starting reel download")

    output_template = MEDIA_DIR / "%(id)s.%(ext)s"

    # --- yt-dlp command selection ---
    if DEBUG:
        logger.info("DEBUG mode enabled — downloading without cookies")
        command = [
            "yt-dlp",
            "-f",
            "best",
            "-o",
            str(output_template),
            url,
        ]
    else:
        logger.info("PROD mode — downloading with cookies")
        command = [
            "yt-dlp",
            "--cookies",
            INSTAGRAM_COOKIES_PATH,
            "-f",
            "best",
            "-o",
            str(output_template),
            url,
        ]

    logger.debug("yt-dlp command: %s", " ".join(command))

    # --- Execute download ---
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        logger.error("yt-dlp failed")
        logger.error("stdout: %s", result.stdout)
        logger.error("stderr: %s", result.stderr)
        raise RuntimeError("Failed to download Instagram reel")

    # --- Locate downloaded file ---
    files = list(MEDIA_DIR.glob("*.mp4"))
    if not files:
        logger.error("Download succeeded but no mp4 file found")
        raise RuntimeError("Video download failed")

    video_path = files[-1]
    logger.info("Reel downloaded successfully: %s", video_path)

    return video_path
