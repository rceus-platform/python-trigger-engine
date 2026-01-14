import json
from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import ReelInsight
from core.services.audio_extractor import extract_audio, extract_audio_for_gemini
from core.services.gemini_transcriber import gemini_transcribe
from core.services.recall import get_daily_triggers
from core.services.reel_downloader import download_reel
from core.services.speech_to_text import transcribe_audio
from core.services.translator import normalize_hindi_to_devanagari, translate_to_english
from core.services.trigger_gemini import extract_triggers_gemini

USE_GEMINI_ASR = True


@csrf_exempt
def process_reel(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Missing 'url' field"}, status=400)

    url = data.get("url")
    if not url:
        return JsonResponse({"error": "Missing 'url' field"}, status=400)

    if "instagram.com" not in url:
        return JsonResponse({"error": "Invalid Instagram URL"}, status=400)

    video_path = download_reel(url)

    if USE_GEMINI_ASR:
        audio_path = extract_audio_for_gemini(video_path)
        result = gemini_transcribe(str(audio_path))

        language = result["language"]
        transcript_original = result["transcript_native"]
        transcript_english = result["transcript_english"]
    else:
        # existing Whisper pipeline
        audio_path = extract_audio(video_path)
        language, raw_transcript = transcribe_audio(audio_path)

        if language == "hi":
            transcript_original = normalize_hindi_to_devanagari(raw_transcript)
            transcript_english = translate_to_english(transcript_original)

        elif language == "mr":
            transcript_original = raw_transcript  # already Devanagari normally
            transcript_english = translate_to_english(transcript_original)

        else:  # en
            transcript_original = raw_transcript
            transcript_english = raw_transcript

    # Triggers always from English
    triggers = extract_triggers_gemini(transcript_english)

    insight = ReelInsight.objects.create(
        source_url=url,
        original_language=language,
        transcript_original=transcript_original,
        transcript_english=transcript_english,
        triggers="\n".join(triggers),
    )

    return JsonResponse(
        {
            "status": "saved",
            "id": insight.id,
            "language": language,
            "transcript_original": transcript_original,
            "transcript_english": transcript_english,
            "triggers": triggers,
        }
    )


def daily_recall(request):
    triggers = get_daily_triggers(limit=5)

    return JsonResponse(
        {
            "date": date.today().isoformat(),
            "count": len(triggers),
            "triggers": triggers,
        }
    )
