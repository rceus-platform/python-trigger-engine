"""Download images from Instagram posts (single image or carousel).

Robust multi-strategy approach (all cookie-aware):
  1. Instaloader with session cookies
  2. Embed page scraping via curl-cffi
  3. Direct page fetch with browser impersonation + JSON / meta-tag extraction
  4. yt-dlp thumbnail extraction (uses Netscape cookie file)
"""

import json
import logging
import re
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import instaloader
import requests as plain_requests
from curl_cffi import requests as curl_requests
from parsel import Selector

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------


def _load_cookies_dict() -> dict[str, str]:
    """Load Instagram Netscape cookies file into a simple {name: value} dict."""
    from core.constants import INSTAGRAM_COOKIES_PATH

    path = Path(INSTAGRAM_COOKIES_PATH)
    if not path.exists():
        return {}

    try:
        jar = MozillaCookieJar(str(path))
        jar.load(ignore_discard=True, ignore_expires=True)
        return {c.name: c.value for c in jar if ".instagram.com" in (c.domain or "")}
    except Exception as e:
        logger.warning("Failed to load cookies from %s: %s", path, e)
        return {}


def _cookies_path_if_exists() -> str | None:
    """Return the cookie file path string if it exists, else None."""
    from core.constants import INSTAGRAM_COOKIES_PATH

    path = Path(INSTAGRAM_COOKIES_PATH)
    return str(path) if path.exists() else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_shortcode(post_url: str) -> str:
    cleaned = post_url.strip().split("?")[0].rstrip("/")
    parts = [part for part in cleaned.split("/") if part]
    if not parts:
        raise RuntimeError("Invalid Instagram post URL")
    return parts[-1]


def _save_image_from_url(
    image_url: str,
    shortcode: str,
    suffix: str = "fallback",
    **req_kwargs,
) -> Path:
    """Download a single image URL and save it to MEDIA_DIR."""
    image_url = image_url.replace("&amp;", "&").replace("\\u0026", "&")
    resp = curl_requests.get(image_url, timeout=20, **req_kwargs)
    resp.raise_for_status()
    save_path = MEDIA_DIR / f"{shortcode}_{suffix}.jpg"
    save_path.write_bytes(resp.content)
    logger.info("Saved fallback image: %s (%d bytes)", save_path.name, len(resp.content))
    return save_path


def _extract_values_by_key(obj, target_key):
    """Recursively collect all values matching *target_key* in a nested structure."""
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


def _download_image(
    loader: instaloader.Instaloader,
    target_stem: Path,
    image_url: str,
    date_utc,
) -> Path:
    loader.download_pic(str(target_stem), image_url, date_utc)
    candidates = sorted(
        target_stem.parent.glob(f"{target_stem.name}.*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"Downloaded image file not found for {target_stem.name}")


def _extract_image_from_html(html: str) -> str | None:
    """Try multiple methods to find a post image URL in raw HTML."""
    sel = Selector(text=html)

    # 1) og:image / twitter:image meta tags
    image_url = (
        sel.xpath('//meta[@property="og:image"]/@content').get()
        or sel.xpath('//meta[@name="twitter:image"]/@content').get()
    )
    if image_url:
        return image_url

    # 2) JSON in <script type="application/json"> tags
    for script in sel.css('script[type="application/json"]::text').getall():
        if "display_url" not in script:
            continue
        try:
            j = json.loads(script)
            urls = _extract_values_by_key(j, "display_url")
            if urls and isinstance(urls[0], str) and urls[0].startswith("http"):
                return urls[0]
        except json.JSONDecodeError:
            continue

    # 3) Regex for display_url
    match = re.search(r'"display_url"\s*:\s*"([^"]+)"', html)
    if match:
        return match.group(1).replace("\\u0026", "&")

    # 4) Any scontent CDN image URL
    match = re.search(
        r'"(https://scontent[a-z0-9.-]*\.cdninstagram\.com/[^"]+\.jpg[^"]*)"', html
    )
    if match:
        return match.group(1).replace("\\u0026", "&")

    return None


# ---------------------------------------------------------------------------
# Strategy 1: Instaloader (with session cookie injection)
# ---------------------------------------------------------------------------


def _try_instaloader(post_url: str, shortcode: str) -> list[Path]:
    """Use instaloader to fetch post images. Injects cookies if available."""
    loader = instaloader.Instaloader(
        download_video_thumbnails=False,
        download_videos=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
    )
    _orig_send = loader.context._session.send

    def _send_with_timeout(request, **kwargs):
        kwargs.setdefault("timeout", 30)
        return _orig_send(request, **kwargs)

    loader.context._session.send = _send_with_timeout

    # Inject cookies from Netscape file into Instaloader's session
    cookies = _load_cookies_dict()
    if cookies:
        logger.info("Injecting %d cookies into Instaloader session", len(cookies))
        for name, value in cookies.items():
            loader.context._session.cookies.set(name, value, domain=".instagram.com")

    post = instaloader.Post.from_shortcode(loader.context, shortcode)
    paths: list[Path] = []

    if post.typename == "GraphSidecar":
        for idx, node in enumerate(post.get_sidecar_nodes()):
            if node.is_video:
                continue
            paths.append(
                _download_image(
                    loader,
                    MEDIA_DIR / f"{shortcode}_{idx}",
                    node.display_url,
                    post.date_utc,
                )
            )
    elif not post.is_video:
        paths.append(
            _download_image(
                loader,
                MEDIA_DIR / f"{shortcode}_0",
                post.url,
                post.date_utc,
            )
        )

    if not paths:
        raise RuntimeError("No downloadable images found via Instaloader")
    return paths


# ---------------------------------------------------------------------------
# Strategy 2: Embed page scraping (cookie-aware)
# ---------------------------------------------------------------------------


def _try_embed_page(shortcode: str) -> list[Path]:
    """Fetch the /embed/ page — sometimes works without auth, better with cookies."""
    cookies = _load_cookies_dict()
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"

    resp = curl_requests.get(
        embed_url, impersonate="chrome", timeout=20, cookies=cookies or None
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embed page returned HTTP {resp.status_code}")

    html = resp.text
    paths: list[Path] = []

    # --- JSON extraction from <script> tags ---
    sel = Selector(text=html)
    for script_content in sel.css("script::text").getall():
        if "display_url" not in script_content and "display_resources" not in script_content:
            continue
        try:
            json_data = json.loads(script_content)
        except json.JSONDecodeError:
            # May be a JS assignment like `window.__additionalData = {...}`
            match = re.search(r"=\s*(\{.+\})\s*;?\s*$", script_content)
            if match:
                try:
                    json_data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
            else:
                continue

        # Carousel
        sidecar_edges = _extract_values_by_key(json_data, "edge_sidecar_to_children")
        if sidecar_edges:
            for sidecar in sidecar_edges:
                edges = sidecar.get("edges", []) if isinstance(sidecar, dict) else []
                for idx, edge in enumerate(edges):
                    node = edge.get("node", {}) if isinstance(edge, dict) else {}
                    url = node.get("display_url", "")
                    if url and not node.get("is_video", False):
                        paths.append(
                            _save_image_from_url(
                                url, shortcode, f"embed_{idx}", impersonate="chrome"
                            )
                        )
            if paths:
                return paths

        # Single image
        display_urls = _extract_values_by_key(json_data, "display_url")
        if display_urls:
            img_url = display_urls[0]
            if isinstance(img_url, str) and img_url.startswith("http"):
                return [
                    _save_image_from_url(
                        img_url, shortcode, "embed_0", impersonate="chrome"
                    )
                ]

    # --- Regex fallback ---
    image_url = _extract_image_from_html(html)
    if image_url:
        return [
            _save_image_from_url(image_url, shortcode, "embed_0", impersonate="chrome")
        ]

    raise RuntimeError("No image found in embed page")


# ---------------------------------------------------------------------------
# Strategy 3: Direct page fetch with cookies + multiple impersonations
# ---------------------------------------------------------------------------


def _try_direct_page(post_url: str, shortcode: str) -> list[Path]:
    """Fetch the main post page with cookies and browser impersonation."""
    cookies = _load_cookies_dict()
    strategies = [
        {"impersonate": "chrome"},
        {"impersonate": "safari"},
        {"headers": {"User-Agent": "facebookexternalhit/1.1"}},
        {"headers": {"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"}},
    ]

    last_err = None
    for strategy in strategies:
        try:
            resp = curl_requests.get(
                post_url, timeout=15, cookies=cookies or None, **strategy
            )
            if resp.status_code != 200:
                continue

            image_url = _extract_image_from_html(resp.text)
            if image_url:
                return [
                    _save_image_from_url(
                        image_url, shortcode, "direct", impersonate="chrome"
                    )
                ]

        except Exception as strategy_err:
            last_err = strategy_err
            continue

    raise RuntimeError("All direct-page strategies failed") from last_err


# ---------------------------------------------------------------------------
# Strategy 4: yt-dlp thumbnail extraction (with Netscape cookie file)
# ---------------------------------------------------------------------------


def _try_ytdlp_thumbnail(post_url: str, shortcode: str) -> list[Path]:
    """Use yt-dlp to extract the post thumbnail URL (supports cookie auth)."""
    import yt_dlp

    cookies_path = _cookies_path_if_exists()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(post_url, download=False)

    thumbnail = info.get("thumbnail")
    thumbnails = info.get("thumbnails", [])

    # Prefer the largest thumbnail
    if thumbnails:
        best = max(thumbnails, key=lambda t: t.get("width", 0) * t.get("height", 0))
        thumbnail = best.get("url") or thumbnail

    if not thumbnail:
        raise RuntimeError("yt-dlp returned no thumbnail for post")

    # Download the thumbnail
    save_path = MEDIA_DIR / f"{shortcode}_ytdlp.jpg"
    resp = plain_requests.get(thumbnail, timeout=20, stream=True)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)
    logger.info("Saved yt-dlp thumbnail: %s (%d bytes)", save_path.name, len(resp.content))
    return [save_path]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def download_instagram_post(post_url: str) -> list[Path]:
    """Download an Instagram post and return local image paths.

    Tries four strategies in order, stopping at the first that succeeds.
    All strategies are cookie-aware when /opt/cookies/instagram.txt exists.
    """
    shortcode = _extract_shortcode(post_url)

    fallback_chain = [
        ("Instaloader", lambda: _try_instaloader(post_url, shortcode)),
        ("Embed page", lambda: _try_embed_page(shortcode)),
        ("Direct page", lambda: _try_direct_page(post_url, shortcode)),
        ("yt-dlp thumbnail", lambda: _try_ytdlp_thumbnail(post_url, shortcode)),
    ]

    last_err = None
    for name, strategy_fn in fallback_chain:
        try:
            paths = strategy_fn()
            if paths:
                logger.info("Strategy '%s' succeeded for post %s", name, shortcode)
                return paths
        except Exception as e:
            logger.warning(
                "Strategy '%s' failed for post %s: %s", name, shortcode, e
            )
            last_err = e

    raise RuntimeError(
        f"All download strategies failed for post {shortcode}"
    ) from last_err
