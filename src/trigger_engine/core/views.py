"""Views that power the Trigger Engine HTTP endpoints."""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from trigger_engine.core.models import ReelInsight
from trigger_engine.core.services.processor import is_instagram_post_url, process_reel_task
from trigger_engine.core.services.recall_service import get_daily_triggers
from trigger_engine.core.services.reel_downloader import get_reel_metadata

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
                return JsonResponse({"status": "processing", "id": existing.pk})

        # Metadata check (source_id)
        source_id = None
        if not is_instagram_post_url(url):
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
                            return JsonResponse({"status": "processing", "id": existing.pk})
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to check metadata cache: %s", e)

        # Create PENDING record
        insight = ReelInsight.objects.create(
            source_url=url,
            source_id=source_id,
            title="Processing...",
            transcript_original="Analysis in progress...",
            transcript_english="Analysis in progress...",
            triggers="Processing...",
        )

        # Process synchronously (delegates heavy pipeline to processor service)
        process_reel_task(insight.pk, url)

        # Refresh from DB to get the results
        insight.refresh_from_db()

        return JsonResponse(
            {
                "status": "complete",
                "id": insight.pk,
                "title": insight.title,
                "triggers": insight.triggers.split("\n") if insight.triggers else [],
                "transcript_original": insight.transcript_original,
                "transcript_english": insight.transcript_english,
                "language": insight.original_language,
            }
        )

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
                    "triggers": insight.triggers.split("\n") if insight.triggers else [],
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
            "date": timezone.localdate().isoformat(),
            "count": len(triggers),
            "triggers": triggers,
        }
    )


def health_check(_request):
    """Report basic health status for the API."""
    return JsonResponse({"status": "healthy", "message": "Trigger Engine API is running"})
