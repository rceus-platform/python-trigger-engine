"""Simple helpers for hashing audio files."""

import hashlib


def compute_audio_hash(path) -> str:
    """Compute the SHA-256 hash of the given file path."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
