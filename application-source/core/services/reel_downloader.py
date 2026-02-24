"""Download utilities that fetch Instagram reels."""

import logging
import os
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

    base_command = [
        "yt-dlp",
        "-f",
        "b",
        "-o",
        str(output_template),
    ]

    command_variants: list[list[str]] = []
    cookies_path = Path(INSTAGRAM_COOKIES_PATH)
    if cookies_path.exists():
        logger.info(
            "Instagram cookies file found: trying cookie-authenticated download"
        )
        command_variants.append(
            [*base_command, "--cookies", INSTAGRAM_COOKIES_PATH, url]
        )
    elif DEBUG:
        browser = os.getenv("INSTAGRAM_COOKIES_BROWSER", "chrome")
        logger.info("No cookies file found; trying browser cookies via: %s", browser)
        command_variants.append([*base_command, "--cookies-from-browser", browser, url])
    elif not DEBUG:
        logger.warning(
            "INSTAGRAM_COOKIES_PATH does not exist: %s", INSTAGRAM_COOKIES_PATH
        )

    command_variants.append([*base_command, url])

    last_stderr = ""
    for command in command_variants:
        logger.debug("yt-dlp command: %s", " ".join(command))
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            break

        logger.error("yt-dlp failed")
        logger.error("stdout: %s", result.stdout)
        logger.error("stderr: %s", result.stderr)
        last_stderr = result.stderr
    else:
        if "empty media response" in last_stderr.lower():
            raise RuntimeError(
                "Instagram blocked this reel for anonymous access. "
                "Provide cookies or use a public reel URL."
            )
        raise RuntimeError("Failed to download Instagram reel")

    # --- Locate downloaded file ---
    files = list(MEDIA_DIR.glob("*.mp4"))
    if not files:
        logger.error("Download succeeded but no mp4 file found")
        raise RuntimeError("Video download failed")

    video_path = files[-1]
    logger.info("Reel downloaded successfully: %s", video_path)

    return video_path
