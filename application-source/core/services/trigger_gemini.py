"""Gemini trigger generator with per-key cooldowns."""

import logging

from google import genai
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS
from core.services.gemini_key_manager import GeminiKeyManager

logger = logging.getLogger(__name__)

MODEL = "models/gemini-2.5-flash-lite"
KEY_MANAGER = GeminiKeyManager()


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

    for _ in range(KEY_MANAGER.key_count):
        api_key = KEY_MANAGER.next_key()
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
                KEY_MANAGER.cooldown_key(api_key)
                continue

            # ---- INVALID KEY ----
            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini trigger API key invalid",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                KEY_MANAGER.disable_key(api_key)
                continue

            logger.exception("Gemini trigger generation failed")
            raise RuntimeError("Trigger generation failed") from e

    raise RuntimeError(
        "All Gemini keys exhausted for trigger generation"
    ) from last_error


def generate_reel_title(transcript_english: str) -> str:
    """
    Returns a catchy, short title (max 5-6 words) for the reel.
    """

    prompt = f"""
Create a catchy, ultra-concise title (max 5-6 words) for an Instagram reel based on this content.
Output ONLY the title string, no quotes or intro.

CONTENT:
{transcript_english}
"""

    last_error = None

    for _ in range(KEY_MANAGER.key_count):
        api_key = KEY_MANAGER.next_key()
        client = genai.Client(api_key=api_key)

        try:
            logger.info(
                "Gemini title generation attempt",
                extra={"key_index": GEMINI_API_KEYS.index(api_key)},
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )

            text = response.text.strip() if response.text else ""

            if not text:
                return "New Reel Processed"

            # Remove potential surrounding quotes
            return text.strip('"').strip("'").strip()

        except ClientError as e:
            error_text = str(e)
            last_error = e

            if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                logger.warning(
                    "Gemini title quota exceeded for key",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                KEY_MANAGER.cooldown_key(api_key)
                continue

            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini title API key invalid",
                    extra={"key_index": GEMINI_API_KEYS.index(api_key)},
                )
                KEY_MANAGER.disable_key(api_key)
                continue

            logger.exception("Gemini title generation failed")
            raise RuntimeError("Title generation failed") from e

    logger.warning("All Gemini keys exhausted for title generation, using default")
    return "New Reel Processed"
