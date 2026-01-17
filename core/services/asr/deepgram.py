import logging
from pathlib import Path

import requests

from core.constants import DEEPGRAM_API_KEY

from .base import ASRProvider
from .errors import ASRFatalError, ASRQuotaExceeded, ASRTemporaryError

logger = logging.getLogger(__name__)


class DeepgramASR(ASRProvider):
    name = "deepgram"

    def __init__(self):
        if not DEEPGRAM_API_KEY:
            raise RuntimeError("DEEPGRAM_API_KEY not configured")

        self.endpoint = "https://api.deepgram.com/v1/listen"
        self.headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
        }

    def transcribe(self, audio_path: str) -> dict:
        logger.info("Deepgram ASR started (REST)")

        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise ASRFatalError("Audio file not found")

        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
            "language": "multi",
        }

        try:
            with audio_file.open("rb") as f:
                response = requests.post(
                    self.endpoint,
                    headers=self.headers,
                    params=params,
                    data=f,
                    timeout=60,
                )

            if response.status_code == 429:
                raise ASRQuotaExceeded("Deepgram quota exceeded")

            if response.status_code >= 500:
                raise ASRTemporaryError("Deepgram server error")

            if response.status_code != 200:
                raise ASRTemporaryError(
                    f"Deepgram error {response.status_code}: {response.text}"
                )

            payload = response.json()
            return self._normalize_response(payload)

        except requests.Timeout:
            raise ASRTemporaryError("Deepgram timeout")

        except requests.ConnectionError:
            raise ASRTemporaryError("Deepgram connection error")

        except ASRFatalError:
            raise

        except Exception as e:
            logger.exception("Deepgram ASR failed")
            raise ASRTemporaryError(str(e))

    # ============================================================
    # Response normalization
    # ============================================================

    def _normalize_response(self, payload: dict) -> dict:
        try:
            alt = payload["results"]["channels"][0]["alternatives"][0]
            transcript = alt["transcript"].strip()

            if not transcript:
                raise ASRFatalError("No speech detected")

            language = payload["results"].get("metadata", {}).get("language", "en")

            if language.startswith("hi"):
                lang = "hi"
            elif language.startswith("mr"):
                lang = "mr"
            else:
                lang = "en"

            return {
                "language": lang,
                "transcript_native": transcript,
                "transcript_english": transcript,
            }

        except ASRFatalError:
            raise

        except Exception:
            logger.exception("Failed to normalize Deepgram response")
            raise ASRTemporaryError("Invalid Deepgram response")
