"""Views that power the Trigger Engine endpoints."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, cast

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from core.models import ReelInsight
from core.services.audio_extractor import extract_audio_for_gemini
from core.services.audio_hash import compute_audio_hash
from core.services.gemini_transcriber import gemini_transcribe
from core.services.post_gemini import extract_post_text
from core.services.post_text_aggregator import download_instagram_post
from core.services.recall import get_daily_triggers
from core.services.reel_downloader import download_reel
from core.services.trigger_gemini import extract_triggers_gemini

logger = logging.getLogger(__name__)
FAVICON_PATH = Path(__file__).resolve().parent.parent / "static" / "favicon.png"


def ui_index(request):
    """Render the single-page UI for the trigger engine."""

    logger.info("UI index accessed")
    return render(request, "core/index.html")


def favicon(_request):
    """Serve favicon without relying on external static setup."""

    if not FAVICON_PATH.exists():
        return HttpResponse(status=404)
    return HttpResponse(FAVICON_PATH.read_bytes(), content_type="image/png")


def _error(message: str, status: int):
    """Create a consistent JSON error response."""

    return JsonResponse({"error": {"message": message}}, status=status)


def _is_instagram_post_url(url: str) -> bool:
    return "/p/" in url


@csrf_exempt
def process_reel(request):
    """Process an Instagram reel and return extracted triggers."""
    # MUST exist for finally block
    video_path = None
    audio_path = None
    image_paths: list[Path] = []

    logger.info("process_reel request started")

    try:
        # --- Method check ---
        if request.method != "POST":
            logger.warning("Invalid HTTP method: %s", request.method)
            return _error("POST required", 405)

        # --- Input parsing ---
        url = request.POST.get("url")

        if not url:
            try:
                data = json.loads(request.body or "{}")
                url = data.get("url")
            except json.JSONDecodeError:
                logger.warning("Invalid JSON body")
                url = None

        if not url:
            logger.warning("Missing URL in request")
            return _error("Missing 'url' field", 400)

        if "instagram.com" not in url:
            logger.warning("Invalid Instagram URL: %s", url)
            return _error("Invalid Instagram URL", 400)

        logger.info("Processing Instagram URL: %s", url)

        # --- Cache by source URL ---
        existing = cast(Any, ReelInsight).objects.filter(source_url=url).first()  # pylint: disable=no-member
        if existing:
            logger.info("Cache hit by source_url (id=%s)", existing.pk)
            return JsonResponse(
                {
                    "status": "cached",
                    "id": existing.pk,
                    "language": existing.original_language,
                    "transcript_original": existing.transcript_original,
                    "transcript_english": existing.transcript_english,
                    "triggers": existing.triggers.split("\n"),
                },
                json_dumps_params={"ensure_ascii": False},
            )

        audio_hash = None
        if _is_instagram_post_url(url):
            logger.info("Detected Instagram post URL, downloading images")
            try:
                image_paths = download_instagram_post(url)
            except RuntimeError as e:
                logger.warning("Post download error: %s", e)
                return _error(str(e), 400)

            logger.info("Downloaded %s post images", len(image_paths))

            try:
                result = extract_post_text(image_paths)
            except RuntimeError as e:
                logger.warning("Post text extraction error: %s", e)
                return _error(str(e), 429)

            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]
        else:
            # --- Download ---
            logger.info("Downloading reel")
            try:
                video_path = download_reel(url)
            except RuntimeError as e:
                logger.warning("Reel download error: %s", e)
                return _error(str(e), 400)
            logger.info("Video downloaded to %s", video_path)

            # --- Audio extraction ---
            logger.info("Extracting audio")
            audio_path = extract_audio_for_gemini(video_path)
            logger.info("Audio extracted to %s", audio_path)

            # --- Audio hash ---
            logger.info("Computing audio hash")
            audio_hash = compute_audio_hash(audio_path)
            logger.info("Audio hash: %s", audio_hash)

            existing = (
                cast(Any, ReelInsight).objects.filter(audio_hash=audio_hash).first()
            )  # pylint: disable=no-member
            if existing:
                logger.info("Cache hit by audio_hash (id=%s)", existing.pk)
                return JsonResponse(
                    {
                        "status": "cached",
                        "id": existing.pk,
                        "language": existing.original_language,
                        "transcript_original": existing.transcript_original,
                        "transcript_english": existing.transcript_english,
                        "triggers": existing.triggers.split("\n"),
                    },
                    json_dumps_params={"ensure_ascii": False},
                )

            # --- Audio validation ---
            size = audio_path.stat().st_size
            logger.info("Audio size: %s bytes", size)

            if size < 50_000:
                logger.warning("Audio too small (%s bytes), likely no speech", size)
                return _error("No speech detected in audio.", 400)

            # --- Gemini transcription ---
            logger.info("Calling Gemini for transcription")
            try:
                result = gemini_transcribe(str(audio_path))
            except RuntimeError as e:
                logger.warning("Gemini error: %s", e)
                return _error(str(e), 429)

            logger.info("Gemini transcription completed")

            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]

        # --- Trigger generation ---
        logger.info("Generating behavior triggers")
        triggers = extract_triggers_gemini(transcript_english)
        logger.info("Generated %s triggers", len(triggers))

        # --- Persist ---
        logger.info("Saving ReelInsight to DB")
        # Create temporary object and set audio path before saving
        insight = ReelInsight(
            source_url=url,
            audio_hash=audio_hash,
            original_language=language,
            transcript_original=transcript_original,
            transcript_english=transcript_english,
            triggers="\n".join(triggers),
        )
        if audio_path:
            setattr(insight, "audio_path_for_email", str(audio_path))
        insight.save()  # This triggers the post_save signal
        logger.info("Saved ReelInsight id=%s", insight.pk)

        # --- Success ---
        logger.info("process_reel completed successfully (id=%s)", insight.pk)
        return JsonResponse(
            {
                "status": "saved",
                "id": insight.pk,
                "language": language,
                "transcript_original": transcript_original,
                "transcript_english": transcript_english,
                "triggers": triggers,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception:  # pylint: disable=broad-exception-caught
        # FULL traceback here
        logger.exception("process_reel failed with unexpected error")
        return _error(
            "Internal processing error. Please try again later.",
            500,
        )

    finally:
        # --- Cleanup ALWAYS ---
        try:
            if video_path:
                video_path.unlink(missing_ok=True)
                logger.info("Cleaned up video file")
            for image_path in image_paths:
                image_path.unlink(missing_ok=True)
            if image_paths:
                logger.info("Cleaned up %s post images", len(image_paths))
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Failed during cleanup")


def daily_recall():
    """Return the latest recall triggers in JSON."""

    logger.info("daily_recall accessed")
    triggers = get_daily_triggers(limit=5)

    return JsonResponse(
        {
            "date": date.today().isoformat(),
            "count": len(triggers),
            "triggers": triggers,
        }
    )


def health_check():
    """Report basic health status for the API."""

    return JsonResponse(
        {"status": "healthy", "message": "Trigger Engine API is running"}
    )
