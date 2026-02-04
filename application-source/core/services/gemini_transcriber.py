import base64
import json
import logging
import time

from google import genai
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS

logger = logging.getLogger(__name__)

MODEL = "models/gemini-flash-lite-latest"
KEY_COOLDOWN_SECONDS = 60 * 60  # 1 hour


# ---- internal key state ----
_KEY_INDEX = {"value": 0}
_key_cooldowns = {key: 0 for key in GEMINI_API_KEYS}


def _get_next_key() -> str:
    now = time.time()
    checked = 0

    while checked < len(GEMINI_API_KEYS):
        key = GEMINI_API_KEYS[_KEY_INDEX["value"]]
        _KEY_INDEX["value"] = (_KEY_INDEX["value"] + 1) % len(GEMINI_API_KEYS)
        checked += 1

        if now >= _key_cooldowns[key]:
            return key

    raise RuntimeError("All Gemini API keys are exhausted. Please retry later.")


def _cooldown_key(key: str):
    _key_cooldowns[key] = time.time() + KEY_COOLDOWN_SECONDS


def gemini_transcribe(audio_path: str) -> dict:
    """
    Returns:
    {
      "language": "hi" | "mr" | "en",
      "transcript_native": "...",
      "transcript_english": "..."
    }
    """

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    # Best-effort MIME type based on file extension
    lower_path = audio_path.lower()
    if lower_path.endswith(".mp3"):
        mime_type = "audio/mpeg"
    elif lower_path.endswith(".wav"):
        mime_type = "audio/wav"
    elif lower_path.endswith(".m4a"):
        mime_type = "audio/mp4"
    else:
        mime_type = "application/octet-stream"

    prompt = """
You are a speech-to-text engine.

Rules:
- Detect the spoken language (Hindi, Marathi, or English)
- If Hindi or Marathi:
  - Output transcript in DEVANAGARI script only
  - Do NOT use Urdu or Roman script
- Preserve English words if spoken
- Also provide a clean English translation
- Do NOT explain anything

Output STRICT JSON only in this format:

{
  "language": "hi|mr|en",
  "transcript_native": "...",
  "transcript_english": "..."
}
"""

    last_error = None

    for _ in range(len(GEMINI_API_KEYS)):
        api_key = _get_next_key()
        client = genai.Client(api_key=api_key)

        try:
            logger.info(
                "Gemini transcription attempt",
                extra={"key_index": GEMINI_API_KEYS.index(api_key)},
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": audio_b64,
                                }
                            },
                            {"text": prompt},
                        ],
                    }
                ],
            )

            response_text = response.text.strip() if response.text else ""
            if not response_text:
                logger.error("Gemini returned empty response text")
                raise RuntimeError("AI returned empty response. Please try again.")

            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error("Gemini returned non-JSON response: %s", response_text[:500])
                raise RuntimeError("AI returned invalid JSON. Please try again.") from e

        except ClientError as e:
            error_text = str(e)
            last_error = e

            # ---- QUOTA / RATE LIMIT ----
            if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                logger.warning(
                    "Gemini quota exceeded for key",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                _cooldown_key(api_key)
                continue

            # ---- INVALID KEY (disable permanently) ----
            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini API key invalid",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                _key_cooldowns[api_key] = float("inf")
                continue

            # ---- other errors ----
            logger.exception("Gemini processing failed")
            raise RuntimeError("AI processing failed. Please try again later.") from e

    raise RuntimeError(
        "AI quota exceeded on all Gemini keys. Please retry later."
    ) from last_error
