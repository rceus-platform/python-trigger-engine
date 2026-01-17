import logging
import time

from .deepgram import DeepgramASR

# from .assemblyai import AssemblyAIASR
# from .deepgram import DeepgramASR
from .errors import ASRQuotaExceeded, ASRTemporaryError
from .gemini import GeminiASR

logger = logging.getLogger(__name__)


class ASRManager:
    def __init__(self):
        self.providers = [
            GeminiASR(),
        ]

        self.cooldowns = {}  # provider_name → unix timestamp

    def _is_available(self, provider):
        until = self.cooldowns.get(provider.name, 0)
        return time.time() >= until

    def _cooldown(self, provider, seconds: int):
        until = time.time() + seconds
        self.cooldowns[provider.name] = until
        logger.warning(
            "ASR provider %s cooling down for %s seconds",
            provider.name,
            seconds,
        )

    def transcribe(self, audio_path: str) -> dict:
        last_error = None

        for provider in self.providers:
            if not self._is_available(provider):
                logger.info("Skipping %s (cooldown active)", provider.name)
                continue

            try:
                logger.info("Trying ASR provider: %s", provider.name)
                return provider.transcribe(audio_path)

            except ASRQuotaExceeded as e:
                last_error = e
                self._cooldown(provider, seconds=600)  # 10 min

            except ASRTemporaryError as e:
                last_error = e
                self._cooldown(provider, seconds=120)  # 2 min

        raise RuntimeError(
            "All transcription providers unavailable. Please retry later."
        ) from last_error
