import logging
import time

from google import genai
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS

logger = logging.getLogger(__name__)

MODEL = "models/gemini-2.5-flash-lite"
KEY_COOLDOWN_SECONDS = 60 * 60  # 1 hour


# ---- internal key state ----
_key_index = 0
_key_cooldowns = {key: 0 for key in GEMINI_API_KEYS}


def _get_next_key() -> str:
    global _key_index

    now = time.time()
    checked = 0

    while checked < len(GEMINI_API_KEYS):
        key = GEMINI_API_KEYS[_key_index]
        _key_index = (_key_index + 1) % len(GEMINI_API_KEYS)
        checked += 1

        if now >= _key_cooldowns[key]:
            return key

    raise RuntimeError("All Gemini API keys exhausted for trigger generation")


def _cooldown_key(key: str):
    _key_cooldowns[key] = time.time() + KEY_COOLDOWN_SECONDS


def extract_triggers_gemini(transcript_english: str) -> list[str]:
    """
    Returns list of behavior triggers from transcript.
    Uses multi-key Gemini fallback.
    """

    prompt = f"""
You are a behavioral coaching system.

Extract clear, actionable behavior triggers from the text below.
Each trigger must be short, concrete, and usable in daily life.

Output rules:
- One trigger per line
- No numbering
- No explanations

TEXT:
{transcript_english}
"""

    last_error = None

    for _ in range(len(GEMINI_API_KEYS)):
        api_key = _get_next_key()
        client = genai.Client(api_key=api_key)

        try:
            logger.info(
                "Gemini trigger generation attempt",
                extra={"key_index": GEMINI_API_KEYS.index(api_key)},
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )

            text = response.text.strip() if response.text else ""

            if not text:
                return []

            return [line.strip() for line in text.splitlines() if line.strip()]

        except ClientError as e:
            error_text = str(e)
            last_error = e

            # ---- QUOTA / RATE LIMIT ----
            if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                logger.warning(
                    "Gemini trigger quota exceeded for key",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                _cooldown_key(api_key)
                continue

            # ---- INVALID KEY ----
            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini trigger API key invalid",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                _key_cooldowns[api_key] = float("inf")
                continue

            logger.exception("Gemini trigger generation failed")
            raise RuntimeError("Trigger generation failed")

    raise RuntimeError(
        "All Gemini keys exhausted for trigger generation"
    ) from last_error
