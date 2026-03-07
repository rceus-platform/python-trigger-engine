"""Tests for the Gemini transcriber service."""

from unittest.mock import MagicMock, mock_open, patch

import pytest
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS
from core.services.gemini_transcriber import gemini_transcribe


def setup_mock_response(mock_client_fixture, text_response):
    """Helper to mutate the autouse mock client for specific tests."""
    mock_response = MagicMock()
    mock_response.text = text_response
    mock_client_fixture.models.generate_content.return_value = mock_response


# Standard test using the conftest global mock (which returns valid JSON)
@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
def test_gemini_transcribe_success(mock_file):
    """Test successful transcription using the conftest global mock."""
    result = gemini_transcribe("test.mp3")
    assert result["title"] == "Mock Title"
    mock_file.assert_called_once_with("test.mp3", "rb")


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
def test_gemini_transcribe_markdown_json(_mock_file, mock_google_genai_client):
    """Test transcription when the response is a markdown JSON block."""
    # Setup response with markdown json block
    setup_mock_response(
        mock_google_genai_client, '```json\n{"language": "en"}\n```'
    )
    result = gemini_transcribe("test.wav")
    assert result["language"] == "en"


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
@patch("core.services.gemini_transcriber.KEY_MANAGER")
def test_gemini_transcribe_empty_response(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test transcription when the AI returns an empty response."""
    setup_mock_response(mock_google_genai_client, "")

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="AI returned empty response"):
        gemini_transcribe("test.m4a")


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
@patch("core.services.gemini_transcriber.KEY_MANAGER")
def test_gemini_transcribe_invalid_json(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test transcription when the AI returns invalid JSON."""
    setup_mock_response(
        mock_google_genai_client, "This is just text, not JSON"
    )

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="AI returned invalid JSON"):
        gemini_transcribe("test.xyz")


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
@patch("core.services.gemini_transcriber.KEY_MANAGER")
def test_gemini_transcribe_quota_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test transcription when a quota error occurs on all keys."""
    # Setup client to raise a ClientError for quota
    error_resp = MagicMock()
    error_resp.text = "RESOURCE_EXHAUSTED quota exceeded"
    error_mock = ClientError(
        "RESOURCE_EXHAUSTED quota exceeded", response=error_resp
    )
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    # Manager has 1 key
    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(
        RuntimeError, match="AI quota exceeded on all Gemini keys"
    ):
        gemini_transcribe("test.mp3")

    mock_key_manager.cooldown_key.assert_called_once_with(valid_key)


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
@patch("core.services.gemini_transcriber.KEY_MANAGER")
def test_gemini_transcribe_invalid_key_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test transcription when an invalid key error occurs."""
    # Setup client to raise a ClientError for invalid key
    error_resp = MagicMock()
    error_resp.text = "API_KEY_INVALID"
    error_mock = ClientError("API_KEY_INVALID", response=error_resp)
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(
        RuntimeError, match="AI quota exceeded on all Gemini keys"
    ):
        gemini_transcribe("test.mp3")

    mock_key_manager.disable_key.assert_called_once_with(valid_key)


@patch("builtins.open", new_callable=mock_open, read_data=b"audio data")
@patch("core.services.gemini_transcriber.KEY_MANAGER")
def test_gemini_transcribe_general_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test transcription when a general client error occurs."""
    # Setup client to raise a different ClientError
    error_resp = MagicMock()
    error_resp.text = "Unknown Error"
    error_mock = ClientError("Unknown Error", response=error_resp)
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="AI processing failed"):
        gemini_transcribe("test.mp3")


@patch("core.services.gemini_transcriber.GEMINI_API_KEYS", ["testkey"])
@patch("core.services.gemini_transcriber.KEY_MANAGER")
@patch("builtins.open", new_callable=MagicMock)
def test_gemini_transcribe_jsondecode_error(mocked_open, mock_key_manager):
    """Test transcription handles JSON decode errors."""
    mock_file = MagicMock()
    mock_file.read.return_value = b"fakeaudio"
    mocked_open.return_value.__enter__.return_value = mock_file

    mock_key_manager.key_count = 1
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "NOT JSON DATA AT ALL"
    mock_client.models.generate_content.return_value = mock_response
    mock_key_manager.get_client.return_value = ("testkey", mock_client)

    with pytest.raises(RuntimeError, match="AI returned invalid JSON"):
        gemini_transcribe("test.mp3")


class FakeClientError(Exception):
    """Fake client error for testing."""


@patch("core.services.gemini_transcriber.GEMINI_API_KEYS", ["testkey"])
@patch("core.services.gemini_transcriber.ClientError", FakeClientError)
@patch("core.services.gemini_transcriber.KEY_MANAGER")
@patch("builtins.open", new_callable=MagicMock)
def test_gemini_transcribe_client_error_quota(mocked_open, mock_key_manager):
    """Test transcription handles quota client errors correctly."""
    mock_file = MagicMock()
    mock_file.read.return_value = b"fakeaudio"
    mocked_open.return_value.__enter__.return_value = mock_file

    mock_key_manager.key_count = 1
    mock_client = MagicMock()

    error = FakeClientError("RESOURCE_EXHAUSTED: Quota Exceeded")
    mock_client.models.generate_content.side_effect = error
    mock_key_manager.get_client.return_value = ("testkey", mock_client)

    with pytest.raises(
        RuntimeError, match="AI quota exceeded on all Gemini keys"
    ):
        gemini_transcribe("test.mp3")

    mock_key_manager.cooldown_key.assert_called_once_with("testkey")


@patch("core.services.gemini_transcriber.GEMINI_API_KEYS", ["testkey"])
@patch("core.services.gemini_transcriber.ClientError", FakeClientError)
@patch("core.services.gemini_transcriber.KEY_MANAGER")
@patch("builtins.open", new_callable=MagicMock)
def test_gemini_transcribe_client_error_invalid_key(
    mocked_open, mock_key_manager
):
    """Test transcription handles invalid key client errors correctly."""
    mock_file = MagicMock()
    mock_file.read.return_value = b"fakeaudio"
    mocked_open.return_value.__enter__.return_value = mock_file

    mock_key_manager.key_count = 1
    mock_client = MagicMock()

    error = FakeClientError("API_KEY_INVALID: Key not valid")
    mock_client.models.generate_content.side_effect = error
    mock_key_manager.get_client.return_value = ("testkey", mock_client)

    with pytest.raises(
        RuntimeError, match="AI quota exceeded on all Gemini keys"
    ):
        gemini_transcribe("test.mp3")

    mock_key_manager.disable_key.assert_called_once_with("testkey")


@patch("core.services.gemini_transcriber.GEMINI_API_KEYS", ["testkey"])
@patch("core.services.gemini_transcriber.ClientError", FakeClientError)
@patch("core.services.gemini_transcriber.KEY_MANAGER")
@patch("builtins.open", new_callable=MagicMock)
def test_gemini_transcribe_client_error_other(mocked_open, mock_key_manager):
    """Test transcription handles other client errors correctly."""
    mock_file = MagicMock()
    mock_file.read.return_value = b"fakeaudio"
    mocked_open.return_value.__enter__.return_value = mock_file

    mock_key_manager.key_count = 1
    mock_client = MagicMock()

    error = FakeClientError("SOME_OTHER_ERROR: Internal Server Error")
    mock_client.models.generate_content.side_effect = error
    mock_key_manager.get_client.return_value = ("testkey", mock_client)

    with pytest.raises(RuntimeError, match="AI processing failed"):
        gemini_transcribe("test.mp3")
