"""Download images from Instagram posts (single image or carousel)."""

import logging
from pathlib import Path

import instaloader

from core.services.instagram_auth import get_instaloader

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
    loader = get_instaloader(download_videos=False)

    shortcode = _extract_shortcode(post_url)
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    image_paths: list[Path] = []

    if post.typename == "GraphSidecar":
        for index, node in enumerate(post.get_sidecar_nodes()):
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

    if not image_paths:
        raise RuntimeError("Instagram post has no downloadable images")

    return image_paths
