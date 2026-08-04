"""Tests for constant evaluations and logic."""

import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

from trigger_engine.core.constants import _get_env_bool


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
            "SITE_PASSCODE": "9999",
        }
    )

    import importlib

    import trigger_engine.core.constants

    with (
        patch("os.path.exists", return_value=True),
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", mock_open(read_data=fake_secrets)),
        patch.dict(os.environ, {}, clear=True),
    ):
        importlib.reload(trigger_engine.core.constants)

        assert trigger_engine.core.constants.GEMINI_API_KEYS == ["test1", "test2"]
        assert trigger_engine.core.constants.EMAIL_HOST_PASSWORD == "pw"
        assert trigger_engine.core.constants.GDRIVE_FOLDER_ID == "gdrive"
        assert trigger_engine.core.constants.SITE_PASSCODE == "9999"

    # Restore module state
    importlib.reload(trigger_engine.core.constants)
