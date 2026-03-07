"""Tests for constant evaluations and logic."""

import json
import os
import sys
from unittest.mock import mock_open, patch

from core.constants import _get_env_bool


def test_get_env_bool():
    """Test environment boolean parsing utility behaves correctly."""
    with patch.dict(os.environ, {"TEST_BOOL": "1"}):
        assert _get_env_bool("TEST_BOOL") is True

    with patch.dict(os.environ, {"TEST_BOOL": "true"}):
        assert _get_env_bool("TEST_BOOL") is True

    with patch.dict(os.environ, {"TEST_BOOL": "False"}):
        assert _get_env_bool("TEST_BOOL") is False

    assert _get_env_bool("MISSING_VAR", default=True) is True
    assert _get_env_bool("MISSING_VAR", default=False) is False


def test_constants_prod_secrets():
    """Test fetching keys directly from prod secrets JSON file if present."""
    fake_secrets = json.dumps(
        {
            "GEMINI_API_KEY_1": "test1",
            "GEMINI_API_KEY_2": "test2",
            "EMAIL_HOST_PASSWORD": "pw",
            "GDRIVE_FOLDER_ID": "gdrive",
            "DEEPGRAM_API_KEY": "dg",
            "SITE_PASSCODE": "9999",
        }
    )

    # We must clear the module to re-evaluate module-level logic
    if "core.constants" in sys.modules:
        del sys.modules["core.constants"]

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_secrets)),
    ):
        import core.constants as constants

        assert constants.GEMINI_API_KEYS == ["test1", "test2"]
        assert constants.EMAIL_HOST_PASSWORD == "pw"
        assert constants.GDRIVE_FOLDER_ID == "gdrive"
        assert constants.DEEPGRAM_API_KEY == "dg"
        assert constants.SITE_PASSCODE == "9999"

    # Re-import cleanly for other tests
    if "core.constants" in sys.modules:
        del sys.modules["core.constants"]
    import core.constants  # noqa: F401
