"""Pipeline processor service for downloading, analyzing, and storing reel insights."""

import logging
import traceback
from pathlib import Path

from django.utils import timezone

from trigger_engine.core.models import ReelInsight
from trigger_engine.core.services.audio_extractor import extract_audio_for_gemini
from trigger_engine.core.services.audio_hash import compute_audio_hash
from trigger_engine.core.services.email_error import send_error_email
from trigger_engine.core.services.email_new_reel import send_new_reel_email
from trigger_engine.core.services.gemini_transcriber import gemini_transcribe
from trigger_engine.core.services.post_downloader import download_instagram_post
from trigger_engine.core.services.post_vision_analyzer import extract_post_text
from trigger_engine.core.services.reel_downloader import download_reel

logger = logging.getLogger(__name__)


def is_instagram_post_url(url: str) -> bool:
    """Check if the given URL points to a standard Instagram post (/p/)."""
    return "/p/" in url


def process_reel_task(insight_id: int, url: str):
    """Synchronously process a reel or post through the AI analysis pipeline."""
    insight = ReelInsight.objects.get(pk=insight_id)
    video_path = None
    audio_path = None
    image_paths: list[Path] = []

    try:
        is_video = not is_instagram_post_url(url)

        if is_instagram_post_url(url):
            try:
                logger.info("Attempting to download post as a video first: %s", url)
                video_path = download_reel(url)
                is_video = True
            except Exception as e:  # noqa: BLE001
                logger.info(
                    "Post is not a video or video download failed, using image workflow: %s",
                    e,
                )
                video_path = None

        if is_video:
            if not video_path:
                video_path = download_reel(url)
            audio_path = extract_audio_for_gemini(video_path)
            audio_hash = compute_audio_hash(audio_path)

            # Secondary dedup check
            existing = (
                ReelInsight.objects.filter(audio_hash=audio_hash).exclude(pk=insight_id).first()
            )
            if existing:
                logger.info("Found duplicate by hash in background, switching to existing")
                insight.original_language = existing.original_language
                insight.transcript_original = existing.transcript_original
                insight.transcript_english = existing.transcript_english
                insight.triggers = existing.triggers
                insight.title = existing.title
                insight.processed_at = timezone.now()
                insight.audio_hash = (
                    None  # Clear instead of duplicate to avoid IntegrityError (unique=True)
                )
                insight.save()
                return

            result = gemini_transcribe(str(audio_path))
            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]
            triggers_list = result.get("triggers", [])
            title = result.get(
                "title",
                "New Reel Processed" if "/reel/" in url else "New Video Post Processed",
            )
        else:
            image_paths = download_instagram_post(url)
            result = extract_post_text(image_paths)
            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]
            triggers_list = result.get("triggers", [])
            title = result.get("title", "New Post Processed")

        insight.original_language = language
        insight.transcript_original = transcript_original
        insight.transcript_english = transcript_english
        insight.triggers = "\n".join(triggers_list)
        insight.title = title
        insight.processed_at = timezone.now()

        if audio_path:
            insight.audio_hash = compute_audio_hash(audio_path)
            insight.audio_path_for_email = str(audio_path)

        insight.save()

        send_new_reel_email(insight, getattr(insight, "audio_path_for_email", None))
        logger.info("Background processing complete for insight %s", insight_id)

    except Exception as e:
        logger.exception("Processing task failed")
        insight.delete()
        send_error_email(url=url, error_message=str(e), traceback_text=traceback.format_exc())
        raise
    finally:
        if video_path:
            video_path.unlink(missing_ok=True)
        for p in image_paths:
            p.unlink(missing_ok=True)
