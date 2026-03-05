"""Download images from Instagram posts (single image or carousel)."""

import logging
import re
from pathlib import Path

import instaloader
import requests

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_DIR.mkdir(exist_ok=True)


def _extract_shortcode(post_url: str) -> str:
    cleaned = post_url.strip().split("?")[0].rstrip("/")
    parts = [part for part in cleaned.split("/") if part]
    if not parts:
        raise RuntimeError("Invalid Instagram post URL")
    return parts[-1]


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


def download_instagram_post(post_url: str) -> list[Path]:
    """Download an Instagram post and return local image paths."""
    loader = instaloader.Instaloader(
        download_video_thumbnails=False,
        download_videos=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
    )
    # Prevent indefinite hangs — instaloader has no built-in timeout.
    # Wrap the session's send() so every request gets a 30 s timeout.
    _orig_send = loader.context._session.send

    def _send_with_timeout(request, **kwargs):
        kwargs.setdefault("timeout", 30)
        return _orig_send(request, **kwargs)

    loader.context._session.send = _send_with_timeout

    shortcode = _extract_shortcode(post_url)
    image_paths: list[Path] = []

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        if post.typename == "GraphSidecar":
            nodes = list(post.get_sidecar_nodes())
            for index, node in enumerate(nodes):
                if node.is_video:
                    continue
                file_path = _download_image(
                    loader=loader,
                    target_stem=MEDIA_DIR / f"{shortcode}_{index}",
                    image_url=node.display_url,
                    date_utc=post.date_utc,
                )
                image_paths.append(file_path)
        elif not post.is_video:
            file_path = _download_image(
                loader=loader,
                target_stem=MEDIA_DIR / f"{shortcode}_0",
                image_url=post.url,
                date_utc=post.date_utc,
            )
            image_paths.append(file_path)

    except Exception as e:
        logger.warning(
            "Instaloader failed to download post %s: %s. Attempting fallback.",
            shortcode,
            e,
        )
        ua = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
        headers = {"User-Agent": ua}
        try:
            resp = requests.get(post_url, headers=headers, timeout=10)
            resp.raise_for_status()

            match = re.search(r'property="og:image"\s+content="([^"]+)"', resp.text)
            if not match:
                raise RuntimeError(
                    f"No og:image found for fallback: {shortcode}"
                ) from e

            image_url = match.group(1).replace("&amp;", "&")
            img_resp = requests.get(image_url, timeout=10)
            img_resp.raise_for_status()

            fallback_path = MEDIA_DIR / f"{shortcode}_fallback.jpg"
            fallback_path.write_bytes(img_resp.content)
            image_paths.append(fallback_path)
        except Exception as fallback_err:
            raise RuntimeError(
                f"Both Instaloader and fallback failed for post {shortcode}"
            ) from fallback_err

    if not image_paths:
        raise RuntimeError("Instagram post has no downloadable images")

    return image_paths
