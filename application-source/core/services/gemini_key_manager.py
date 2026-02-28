"""Shared helper for rotating Gemini API keys."""

import time
from typing import Iterable

from google import genai

from core.constants import GEMINI_API_KEYS

DEFAULT_COOLDOWN_SECONDS = 60 * 60  # 1 hour


class GeminiKeyManager:
    """Stateful manager for Gemini API key rotation and client pooling."""

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
        # Client pool: key -> Client instance
        self._clients: dict[str, genai.Client] = {}

    @property
    def key_count(self) -> int:
        """Return how many keys are managed."""
        return len(self._keys)

    def get_client(self) -> tuple[str, genai.Client]:
        """Return (api_key, Client) for the next available key, pooling instances."""
        now = time.time()
        checked = 0

        while checked < len(self._keys):
            key = self._keys[self._index]
            self._index = (self._index + 1) % len(self._keys)
            checked += 1

            if now >= self._cooldowns[key]:
                if key not in self._clients:
                    self._clients[key] = genai.Client(api_key=key)
                return key, self._clients[key]

        raise RuntimeError("All Gemini API keys are exhausted. Please retry later.")

    def next_key(self) -> str:
        """Legacy helper - preferred to use get_client() for session reuse."""
        key, _ = self.get_client()
        return key

    def cooldown_key(self, key: str) -> None:
        """Put a key on cooldown for the configured duration."""
        self._cooldowns[key] = time.time() + self.cooldown_seconds
        # Optionally drop client on error? Usually better to keep if it's just quota
        # If it's INVALID_KEY, disable_key will handle it

    def disable_key(self, key: str) -> None:
        """Disable a key permanently."""
        self._cooldowns[key] = float("inf")
        self._clients.pop(key, None)
