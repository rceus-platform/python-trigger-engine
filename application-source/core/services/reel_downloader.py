"""Download utilities that fetch Instagram reels."""

import logging
import os
from pathlib import Path

import instaloader
import yt_dlp

from core.constants import INSTAGRAM_COOKIES_PATH
from core.services.instagram_auth import load_cookies_into_session

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


def get_reel_metadata(url: str) -> dict:
    """Fetches metadata for a reel without downloading it."""
    cookies_path = Path(INSTAGRAM_COOKIES_PATH)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if cookies_path.exists():
        ydl_opts["cookiefile"] = str(cookies_path)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info.get("id"),
            "title": info.get("title"),
        }


def download_reel(url: str) -> Path:
    """
    Downloads an Instagram reel and returns the video file path.
    """

    logger.info("Starting reel download")

    # --- Sanity check cookies using Instaloader (as requested) ---
    temp_loader = instaloader.Instaloader()
    cookies_valid = load_cookies_into_session(
        temp_loader.context._session, Path(INSTAGRAM_COOKIES_PATH)
    )
    if not cookies_valid:
        logger.warning("Reel download might fail due to missing/invalid cookies")

    cookies_path = Path(INSTAGRAM_COOKIES_PATH)
    output_template = MEDIA_DIR / "%(id)s.%(ext)s"

    ydl_opts = {
        "format": "best",
        "outtmpl": str(output_template),
        "quiet": True,
        "no_warnings": True,
    }

    if cookies_path.exists():
        logger.info("Using Instagram cookies for download")
        ydl_opts["cookiefile"] = str(cookies_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error("yt-dlp library download failed: %s", e)
        # Fallback logic if needed
        if not ydl_opts.get("cookiefile"):
            logger.info("Attempting fallback with browser cookies (chrome/safari)")
            ydl_opts["cookiesfrombrowser"] = (
                os.getenv("INSTAGRAM_COOKIES_BROWSER", "chrome"),
            )
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as exc:
                raise RuntimeError("Failed download with browser cookies") from exc
        else:
            raise RuntimeError(f"Download failed: {e}") from e

    # --- Locate downloaded file ---
    files = list(MEDIA_DIR.glob("*.mp4"))
    if not files:
        logger.error("Download succeeded but no mp4 file found")
        raise RuntimeError("Video download failed")

    video_path = files[-1]
    logger.info("Reel downloaded successfully: %s", video_path)

    return video_path
