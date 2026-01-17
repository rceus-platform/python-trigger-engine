import base64
import json
import logging
import time

from google import genai
from google.genai.errors import ClientError

from core import constants
from core.constants import GEMINI_API_KEYS
from core.services.asr.base import ASRProvider
from core.services.asr.errors import (
    ASRFatalError,
    ASRQuotaExceeded,
    ASRTemporaryError,
)

logger = logging.getLogger(__name__)


class GeminiASR(ASRProvider):
    """
    Gemini ASR provider using google.genai.Client
    with multi-key rotation and per-key cooldowns.
    """

    name = "gemini"
    MODEL = "models/gemini-flash-lite-latest"
    KEY_COOLDOWN_SECONDS = 60 * 60  # 1 hour

    def __init__(self):
        if not GEMINI_API_KEYS:
            raise RuntimeError("No Gemini API keys configured")

        self.keys = GEMINI_API_KEYS
        self.key_index = 0
        self.key_cooldowns = {key: 0 for key in self.keys}

    # ---------- Internal helpers ----------

    def _get_next_key(self) -> str:
        now = time.time()
        checked = 0

        while checked < len(self.keys):
            key = self.keys[self.key_index]
            self.key_index = (self.key_index + 1) % len(self.keys)
            checked += 1

            if now >= self.key_cooldowns[key]:
                return key

        raise ASRQuotaExceeded("All Gemini API keys are in cooldown")

    def _cooldown_key(self, key: str):
        self.key_cooldowns[key] = time.time() + self.KEY_COOLDOWN_SECONDS

    # ---------- Provider API ----------

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribes audio and returns ENGLISH transcript only.
        Language detection / native script is intentionally excluded
        because ASRManager expects plain text.
        """

        api_key = self._get_next_key()
        client = genai.Client(api_key=api_key)

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()

        prompt = """
You are a speech-to-text engine.
Return ONLY the English transcript.
Do not explain anything.
"""

        try:
            logger.info(
                "Gemini ASR request",
                extra={
                    "provider": "gemini",
                    "key_index": self.keys.index(api_key),
                },
            )

            response = client.models.generate_content(
                model=self.MODEL,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "audio/wav",
                                    "data": audio_b64,
                                }
                            },
                            {"text": prompt},
                        ],
                    }
                ],
            )

            text = response.text.strip() if response.text else ""

            if not text:
                raise ASRFatalError("No speech detected in audio")

            return text

        except ClientError as e:
            error_text = str(e)

            # ---- INVALID API KEY (FATAL FOR THIS KEY) ----
            if "API_KEY_INVALID" in error_text or "not valid" in error_text.lower():
                logger.error(
                    "Gemini API key invalid",
                    extra={
                        "provider": "gemini",
                        "key_index": self.keys.index(api_key),
                    },
                )

                # Disable this key permanently
                self.key_cooldowns[api_key] = float("inf")

                # Try next key immediately
                raise ASRTemporaryError("Gemini API key invalid")

            # ---- QUOTA / RATE LIMIT (TEMPORARY) ----
            if any(x in error_text for x in ["RESOURCE_EXHAUSTED", "Quota", "quota"]):
                self._cooldown_key(api_key)

                logger.warning(
                    "Gemini quota exceeded for key",
                    extra={
                        "provider": "gemini",
                        "key_index": self.keys.index(api_key),
                        "cooldown_seconds": self.KEY_COOLDOWN_SECONDS,
                    },
                )

                raise ASRTemporaryError("Gemini quota exceeded")

            # ---- Fatal ASR ----
            if "no speech" in error_text.lower():
                raise ASRFatalError("No speech in audio")

            logger.exception("Gemini ASR transient error")
            raise ASRTemporaryError("Gemini ASR transient failure")

        except Exception:
            logger.exception("Gemini ASR unknown failure")
            raise ASRTemporaryError("Gemini ASR failed unexpectedly")
