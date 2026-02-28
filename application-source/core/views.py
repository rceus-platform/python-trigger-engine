"""Views that power the Trigger Engine endpoints."""

import json
import logging
import traceback
from datetime import date
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_q.tasks import async_task

from core.models import ReelInsight
from core.services.audio_extractor import extract_audio_for_gemini
from core.services.audio_hash import compute_audio_hash
from core.services.email_error import send_error_email
from core.services.gemini_transcriber import gemini_transcribe
from core.services.post_gemini import extract_post_text
from core.services.post_text_aggregator import download_instagram_post
from core.services.recall import get_daily_triggers
from core.services.reel_downloader import download_reel, get_reel_metadata

logger = logging.getLogger(__name__)
FAVICON_PATH = Path(__file__).resolve().parent.parent / "static" / "favicon.png"


def ui_index(request):
    """Render the single-page UI for the trigger engine."""
    if not (request.user.is_authenticated or request.session.get("is_authenticated")):
        return redirect("auth-gateway")
    return render(request, "core/index.html")


def auth_gateway(request):
    """Entry point for users to choose their authentication method."""
    if request.user.is_authenticated or request.session.get("is_authenticated"):
        return redirect("ui-index")
    return render(request, "core/auth_gateway.html")


def login_passcode(request):
    """Handle 4-pin passcode entry."""
    if request.user.is_authenticated or request.session.get("is_authenticated"):
        return redirect("ui-index")

    error = None
    if request.method == "POST":
        pin = request.POST.get("pin")
        if pin == settings.SITE_PASSCODE:
            request.session["is_authenticated"] = True
            return redirect("ui-index")
        else:
            error = "Invalid PIN"
    return render(request, "core/passcode.html", {"error": error})


def favicon(_request):
    """Serve the favicon for the application."""
    if not FAVICON_PATH.exists():
        return HttpResponse(status=404)
    return HttpResponse(FAVICON_PATH.read_bytes(), content_type="image/png")


def _error(message: str, status: int = 400):
    return JsonResponse({"error": {"message": message}}, status=status)


def _is_instagram_post_url(url: str) -> bool:
    return "/p/" in url


def background_process_reel(insight_id: int, url: str):
    """Background task to process a reel/post."""
    from core.services.email_new_reel import send_new_reel_email

    insight = ReelInsight.objects.get(pk=insight_id)
    video_path = None
    audio_path = None
    image_paths: list[Path] = []

    try:
        if _is_instagram_post_url(url):
            image_paths = download_instagram_post(url)
            result = extract_post_text(image_paths)
            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]
            triggers_list = result.get("triggers", [])
            title = result.get("title", "New Post Processed")
        else:
            video_path = download_reel(url)
            audio_path = extract_audio_for_gemini(video_path)
            audio_hash = compute_audio_hash(audio_path)

            # Secondary dedup check
            existing = (
                ReelInsight.objects.filter(audio_hash=audio_hash)
                .exclude(pk=insight_id)
                .first()
            )
            if existing:
                logger.info(
                    "Found duplicate by hash in background, switching to existing"
                )
                insight.original_language = existing.original_language
                insight.transcript_original = existing.transcript_original
                insight.transcript_english = existing.transcript_english
                insight.triggers = existing.triggers
                insight.title = existing.title
                insight.processed_at = timezone.now()
                insight.audio_hash = existing.audio_hash
                insight.save()
                return

            result = gemini_transcribe(str(audio_path))
            language = result["language"]
            transcript_original = result["transcript_native"]
            transcript_english = result["transcript_english"]
            triggers_list = result.get("triggers", [])
            title = result.get("title", "New Reel Processed")

        insight.original_language = language
        insight.transcript_original = transcript_original
        insight.transcript_english = transcript_english
        insight.triggers = "\n".join(triggers_list)
        insight.title = title
        insight.processed_at = timezone.now()

        if audio_path:
            insight.audio_hash = compute_audio_hash(audio_path)
            setattr(insight, "audio_path_for_email", str(audio_path))

        insight.save()

        send_new_reel_email(insight, getattr(insight, "audio_path_for_email", None))
        logger.info("Background processing complete for insight %s", insight_id)

    except Exception as e:
        logger.exception("Background task failed")
        insight.delete()
        send_error_email(
            url=url, error_message=str(e), traceback_text=traceback.format_exc()
        )
    finally:
        if video_path:
            video_path.unlink(missing_ok=True)
        for p in image_paths:
            p.unlink(missing_ok=True)


@csrf_exempt
@require_POST
def process_reel(request):
    """API endpoint to initiate processing."""
    try:
        data = (
            json.loads(request.body or "{}")
            if request.content_type == "application/json"
            else request.POST
        )
        url = data.get("url")

        if not url or "instagram.com" not in url:
            return _error("Valid Instagram URL required", 400)

        # Cache check by URL
        existing = ReelInsight.objects.filter(source_url=url).first()
        if existing:
            if existing.processed_at:
                return JsonResponse(
                    {
                        "status": "cached",
                        "id": existing.pk,
                        "title": existing.title,
                        "triggers": existing.triggers.split("\n"),
                        "transcript_original": existing.transcript_original,
                        "transcript_english": existing.transcript_english,
                        "language": existing.original_language,
                    }
                )
            else:
                # Already checking/processing
                # If it's been stuck for over 5 minutes without completing, the worker likely crashed. Restart it.
                if (timezone.now() - existing.created_at).total_seconds() > 300:
                    async_task("core.views.background_process_reel", existing.pk, url)
                return JsonResponse({"status": "processing", "id": existing.pk})

        # Metadata check (source_id)
        source_id = None
        if not _is_instagram_post_url(url):
            try:
                meta = get_reel_metadata(url)
                source_id = meta.get("id")
                if source_id:
                    existing = ReelInsight.objects.filter(source_id=source_id).first()
                    if existing:
                        if existing.processed_at:
                            return JsonResponse(
                                {
                                    "status": "cached",
                                    "id": existing.pk,
                                    "title": existing.title,
                                    "triggers": existing.triggers.split("\n"),
                                    "transcript_original": existing.transcript_original,
                                    "transcript_english": existing.transcript_english,
                                    "language": existing.original_language,
                                }
                            )
                        else:
                            # If it's been stuck for over 5 minutes without completing, restart it.
                            if (
                                timezone.now() - existing.created_at
                            ).total_seconds() > 300:
                                async_task(
                                    "core.views.background_process_reel",
                                    existing.pk,
                                    url,
                                )
                            return JsonResponse(
                                {"status": "processing", "id": existing.pk}
                            )
            except Exception:
                pass

        # Create PENDING record
        insight = ReelInsight.objects.create(
            source_url=url,
            source_id=source_id,
            title="Processing...",
            transcript_original="Analysis in progress...",
            transcript_english="Analysis in progress...",
            triggers="Processing...",
        )

        # Enqueue background task
        async_task("core.views.background_process_reel", insight.pk, url)

        return JsonResponse({"status": "processing", "id": insight.pk})

    except Exception as e:
        logger.exception("process_reel endpoint failed")
        return _error(str(e), 500)


def check_task_status(_request, insight_id):
    """API endpoint for frontend polling."""
    try:
        insight = ReelInsight.objects.get(pk=insight_id)
        if insight.processed_at:
            return JsonResponse(
                {
                    "status": "complete",
                    "id": insight.pk,
                    "title": insight.title,
                    "triggers": insight.triggers.split("\n")
                    if insight.triggers
                    else [],
                    "transcript_original": insight.transcript_original,
                    "transcript_english": insight.transcript_english,
                    "language": insight.original_language,
                }
            )
        return JsonResponse({"status": "processing"})
    except ReelInsight.DoesNotExist:
        return _error("Insight not found", 404)


def daily_recall(_request):
    """Return the latest recall triggers in JSON."""
    triggers = get_daily_triggers(limit=5)
    return JsonResponse(
        {
            "date": date.today().isoformat(),
            "count": len(triggers),
            "triggers": triggers,
        }
    )


def health_check(_request):
    """Report basic health status for the API."""
    return JsonResponse(
        {"status": "healthy", "message": "Trigger Engine API is running"}
    )
