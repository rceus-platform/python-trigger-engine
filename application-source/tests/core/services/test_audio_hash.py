"""Tests for audio hashing service."""

import hashlib
from unittest.mock import mock_open, patch

from core.services.audio_hash import compute_audio_hash


def test_compute_audio_hash():
    """Test generating a unique hash from an audio file payload."""
    # Setup mock data for file reading
    mock_data = b"mock audio data"

    # Patch the builtin open function
    with patch("builtins.open", mock_open(read_data=mock_data)) as mocked_file:
        result = compute_audio_hash("dummy/path.mp3")

        # Verify it opened the correct file in binary read mode
        mocked_file.assert_called_once_with("dummy/path.mp3", "rb")

        # We manually compute the hash to ensure our test matches the logic
        expected_hash = hashlib.sha256(mock_data).hexdigest()

        assert result == expected_hash
