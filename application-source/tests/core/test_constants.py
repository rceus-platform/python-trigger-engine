"""Tests for constant evaluations and logic."""

import json
import os
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

    import importlib

    import core.constants

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_secrets)),
        patch.dict(os.environ, {}, clear=True),
    ):
        importlib.reload(core.constants)

        assert core.constants.GEMINI_API_KEYS == ["test1", "test2"]
        assert core.constants.EMAIL_HOST_PASSWORD == "pw"
        assert core.constants.GDRIVE_FOLDER_ID == "gdrive"
        assert core.constants.DEEPGRAM_API_KEY == "dg"
        assert core.constants.SITE_PASSCODE == "9999"

    # Restore module state
    importlib.reload(core.constants)
