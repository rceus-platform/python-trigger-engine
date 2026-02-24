"""Gemini helpers for extracting text from Instagram post images."""

import json
import logging
from mimetypes import guess_type
from pathlib import Path

from google import genai
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS
from core.services.gemini_key_manager import GeminiKeyManager

logger = logging.getLogger(__name__)

MODEL = "models/gemini-2.5-flash-lite"
KEY_MANAGER = GeminiKeyManager()


def _safe_key_index(api_key: str) -> int:
    try:
        return GEMINI_API_KEYS.index(api_key)
    except ValueError:
        return -1


def _parse_json_object(response_text: str) -> dict[str, object]:
    text = response_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        parsed = json.loads(snippet)
        if isinstance(parsed, dict):
            return parsed

    raise RuntimeError("AI returned invalid post text JSON")


def extract_post_text(image_paths: list[Path]) -> dict[str, str]:
    """Extract language + text content from a list of post images."""
    if not image_paths:
        raise RuntimeError("No images found in Instagram post")

    prompt = """
You are an OCR + language normalization engine.

Read all provided Instagram images and extract educational/meaningful text.
Ignore decorative symbols, watermarks, and UI elements.

Return STRICT JSON only in this schema:
{
  "language": "hi|mr|en|mixed",
  "transcript_native": "combined extracted text in original script",
  "transcript_english": "clean natural English translation of the extracted text"
}

Do not wrap JSON in markdown or code fences.
"""

    contents: list[dict[str, object]] = []
    for image_path in image_paths:
        mime_type, _ = guess_type(str(image_path))
        with image_path.open("rb") as image_file:
            contents.append(
                {
                    "inline_data": {
                        "mime_type": mime_type or "image/jpeg",
                        "data": image_file.read(),
                    }
                }
            )
    contents.append({"text": prompt})

    last_error = None

    for _ in range(KEY_MANAGER.key_count):
        api_key = KEY_MANAGER.next_key()
        client = genai.Client(api_key=api_key)

        try:
            logger.info(
                "Gemini post text extraction attempt",
                extra={"key_index": _safe_key_index(api_key)},
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=[{"role": "user", "parts": contents}],
            )

            response_text = response.text.strip() if response.text else ""
            if not response_text:
                raise RuntimeError("AI returned empty post text response")

            try:
                parsed = _parse_json_object(response_text)
            except (json.JSONDecodeError, RuntimeError) as exc:
                logger.error(
                    "Gemini post response was not JSON: %s",
                    response_text[:500],
                )
                raise RuntimeError("AI returned invalid post text JSON") from exc

            language = str(parsed.get("language", "mixed"))
            transcript_native = str(parsed.get("transcript_native", "")).strip()
            transcript_english = str(parsed.get("transcript_english", "")).strip()

            if not transcript_english:
                raise RuntimeError("AI could not extract readable text from the post")

            if not transcript_native:
                transcript_native = transcript_english

            return {
                "language": language,
                "transcript_native": transcript_native,
                "transcript_english": transcript_english,
            }

        except ClientError as exc:
            error_text = str(exc)
            last_error = exc

            if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                logger.warning(
                    "Gemini post extraction quota exceeded for key",
                    extra={"key_index": _safe_key_index(api_key)},
                )
                KEY_MANAGER.cooldown_key(api_key)
                continue

            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini post extraction API key invalid",
                    extra={"key_index": _safe_key_index(api_key)},
                )
                KEY_MANAGER.disable_key(api_key)
                continue

            logger.exception("Gemini post text extraction failed")
            raise RuntimeError("Post text extraction failed") from exc

    raise RuntimeError(
        "All Gemini keys exhausted for post text extraction"
    ) from last_error
