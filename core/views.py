import json
from datetime import date

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from core.models import ReelInsight
from core.services.audio_extractor import extract_audio_for_gemini
from core.services.gemini_transcriber import gemini_transcribe
from core.services.recall import get_daily_triggers
from core.services.reel_downloader import download_reel
from core.services.trigger_gemini import extract_triggers_gemini


def ui_index(request):
    return render(request, "core/index.html")


def _error(message: str, status: int):
    """
    Unified error response.
    Always JSON. Safe for UI.
    """
    return JsonResponse({"error": {"message": message}}, status=status)


@csrf_exempt
def process_reel(request):
    try:
        if request.method != "POST":
            return _error("POST required", 405)

        # Accept both HTML form and JSON
        url = request.POST.get("url")

        if not url:
            try:
                data = json.loads(request.body or "{}")
                url = data.get("url")
            except json.JSONDecodeError:
                url = None

        if not url:
            return _error("Missing 'url' field", 400)

        if "instagram.com" not in url:
            return _error("Invalid Instagram URL", 400)

        # --- Download & audio extraction ---
        video_path = download_reel(url)
        audio_path = extract_audio_for_gemini(video_path)

        # --- Gemini transcription ---
        try:
            result = gemini_transcribe(str(audio_path))
        except RuntimeError as e:
            # Quota / AI-level errors (user actionable)
            return _error(str(e), 429)

        language = result["language"]
        transcript_original = result["transcript_native"]
        transcript_english = result["transcript_english"]

        # --- Trigger generation ---
        triggers = extract_triggers_gemini(transcript_english)

        # --- Persist ---
        insight = ReelInsight.objects.create(
            source_url=url,
            original_language=language,
            transcript_original=transcript_original,
            transcript_english=transcript_english,
            triggers="\n".join(triggers),
        )

        # --- Cleanup (best-effort) ---
        try:
            video_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
        except Exception:
            pass

        # --- Success response ---
        return JsonResponse(
            {
                "status": "saved",
                "id": insight.id,
                "language": language,
                "transcript_original": transcript_original,
                "transcript_english": transcript_english,
                "triggers": triggers,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception:
        # Absolute safety net: NEVER leak HTML / stack traces
        return _error("Internal processing error. Please try again later.", 500)


def daily_recall(request):
    triggers = get_daily_triggers(limit=5)

    return JsonResponse(
        {
            "date": date.today().isoformat(),
            "count": len(triggers),
            "triggers": triggers,
        }
    )


def health_check(request):
    return JsonResponse(
        {"status": "healthy", "message": "Trigger Engine API is running"}
    )
