"""Download utilities that fetch Instagram reels."""

import json
import logging
import re
from pathlib import Path

import requests
import yt_dlp
from curl_cffi import requests as curl_requests
from parsel import Selector

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_shortcode(url: str) -> str:
    """Pull the shortcode out of a /reel/ or /p/ URL."""
    match = re.search(r"/(reel|p)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract shortcode from: {url}")
    return match.group(2)


def _extract_values_by_key(obj, target_key):
    """Recursively collect all values matching target_key in a nested structure."""
    values = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key:
                values.append(v)
            else:
                values.extend(_extract_values_by_key(v, target_key))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(_extract_values_by_key(item, target_key))
    return values


def _download_file(url: str, save_path: Path) -> Path:
    """Stream-download a file from url to save_path using plain requests."""
    logger.info("Downloading from: %s...", url[:80])
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    logger.info("Saved to: %s", save_path)
    return save_path


# ---------------------------------------------------------------------------
# Metadata (unchanged — still uses yt_dlp for dedup via source_id)
# ---------------------------------------------------------------------------


def get_reel_metadata(url: str) -> dict:
    """Fetches metadata for a reel without downloading it."""
    from core.constants import INSTAGRAM_COOKIES_PATH

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


# ---------------------------------------------------------------------------
# Reel downloader (curl_cffi → JSON scrape → .mp4)
# ---------------------------------------------------------------------------


def download_reel(url: str) -> Path:
    """
    Downloads an Instagram reel and returns the video file path.

    Strategy:
      1. Fetch the reel page via curl_cffi (impersonates Chrome, bypasses 403).
      2. Find video_versions URL inside embedded JSON script tags.
      3. Regex fallback: scan raw HTML for .mp4 CDN links.
      4. Stream-download the .mp4 with plain requests.
    """
    shortcode = _extract_shortcode(url)
    save_path = MEDIA_DIR / f"{shortcode}.mp4"

    logger.info("Starting reel download: %s  (shortcode=%s)", url, shortcode)

    resp = curl_requests.get(url, impersonate="chrome")
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch reel page (HTTP {resp.status_code}): {url}"
        )

    selector = Selector(resp.text)
    scripts = selector.css('script[type="application/json"]::text').getall()
    if not scripts:
        scripts = selector.css("script::text").getall()

    # --- Attempt 1: JSON extraction ---
    for script_content in scripts:
        if "video_versions" not in script_content:
            continue
        try:
            json_data = json.loads(script_content)
        except json.JSONDecodeError:
            continue

        video_versions = _extract_values_by_key(json_data, "video_versions")
        for version_list in video_versions:
            try:
                if isinstance(version_list, list) and version_list:
                    video_url = version_list[0].get("url")
                    if video_url:
                        logger.info("Found video URL in JSON.")
                        return _download_file(video_url, save_path)
            except (IndexError, TypeError, AttributeError, KeyError):
                continue

    # --- Attempt 2: Regex fallback ---
    logger.info("JSON parsing missed video; trying Regex fallback…")
    for match in re.findall(r'"(https://instagram\.f[^"]+\.mp4[^"]+)"', resp.text):
        decoded = match.encode().decode("unicode-escape").replace("\\/", "/")
        if decoded:
            logger.info("Found video URL via Regex.")
            return _download_file(decoded, save_path)

    raise RuntimeError(f"Could not find a playable video URL for reel: {url}")
