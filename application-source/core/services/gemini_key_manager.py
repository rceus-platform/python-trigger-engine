"""Shared helper for rotating Gemini API keys."""

import time
from typing import Iterable

from core.constants import GEMINI_API_KEYS

DEFAULT_COOLDOWN_SECONDS = 60 * 60  # 1 hour


class GeminiKeyManager:
    """Stateful manager for Gemini API key rotation."""

    def __init__(
        self,
        keys: Iterable[str] | None = None,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        raw_keys = list(keys) if keys is not None else list(GEMINI_API_KEYS)
        self._keys: list[str] = [key for key in raw_keys if key]
        if not self._keys:
            raise RuntimeError("No Gemini API keys configured.")
        self._index = 0
        self.cooldown_seconds = cooldown_seconds
        self._cooldowns: dict[str, float] = {key: 0.0 for key in self._keys}

    @property
    def key_count(self) -> int:
        """Return how many keys are managed."""
        return len(self._keys)

    def next_key(self) -> str:
        """Return the next available key, raising if all are cooling down."""
        now = time.time()
        checked = 0

        while checked < len(self._keys):
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            checked += 1

            if now >= self._cooldowns[key]:
                return key

        raise RuntimeError("All Gemini API keys are exhausted. Please retry later.")

    def cooldown_key(self, key: str) -> None:
        """Put a key on cooldown for the configured duration."""
        self._cooldowns[key] = time.time() + self.cooldown_seconds

    def disable_key(self, key: str) -> None:
        """Disable a key permanently."""
        self._cooldowns[key] = float("inf")
