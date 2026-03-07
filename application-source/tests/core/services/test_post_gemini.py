"""Tests for the post_gemini service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from google.genai.errors import ClientError

from core.constants import GEMINI_API_KEYS
from core.services.post_gemini import (
    _parse_json_object,
    _safe_key_index,
    extract_post_text,
)


def test_safe_key_index():
    """Test safe key index generation."""
    with patch("core.services.post_gemini.GEMINI_API_KEYS", ["key1", "key2"]):
        assert _safe_key_index("key2") == 1
        assert _safe_key_index("unknown") == -1


def test_parse_json_object_valid():
    """Test parsing a valid JSON object."""
    assert _parse_json_object('{"key": "value"}') == {"key": "value"}


def test_parse_json_object_markdown_wrapper():
    """Test parsing JSON object enclosed in markdown code blocks."""
    # Test with standard markdown
    text = '```json\n{"data": 123}\n```'
    assert _parse_json_object(text) == {"data": 123}


def test_parse_json_object_embedded_snippet():
    """Test parsing JSON object embedded within other text."""
    # Test with garbage text before and after the snippet
    text = 'Here is the response:\n{"inner": "content"}\nHope this helps.'
    assert _parse_json_object(text) == {"inner": "content"}


def test_parse_json_object_invalid():
    """Test parsing invalid JSON object raises RuntimeError."""
    with pytest.raises(
        RuntimeError, match="AI returned invalid post text JSON"
    ):
        _parse_json_object(
            "This is completely free of any braces or json structure"
        )


def setup_mock_response(mock_client_fixture, text_response):
    """Set up the mock client to return a specific text response."""
    mock_response = MagicMock()
    mock_response.text = text_response
    mock_client_fixture.models.generate_content.return_value = mock_response


def test_extract_post_text_no_images():
    """Test extracting post text when no images are provided."""
    with pytest.raises(RuntimeError, match="No images found"):
        extract_post_text([])


@patch("pathlib.Path.open", new_callable=mock_open, read_data=b"image bytes")
def test_extract_post_text_success(_mock_file, mock_google_genai_client):
    """Test successfully extracting post text."""
    response_json = {
        "language": "en",
        "transcript_native": "Original strict",
        "transcript_english": "English variant",
        "triggers": ["T1"],
        "title": "Title",
    }
    setup_mock_response(mock_google_genai_client, json.dumps(response_json))

    result = extract_post_text([Path("dummy.jpg")])

    assert result["language"] == "en"
    assert result["transcript_english"] == "English variant"
    assert result["triggers"] == ["T1"]
    _mock_file.assert_called_once_with("rb")


@patch("pathlib.Path.open", new_callable=mock_open, read_data=b"image bytes")
def test_extract_post_text_fallback_native_transcript(
    _mock_file, mock_google_genai_client
):
    """Test extracting post text when native transcript is empty."""
    response_json = {
        "transcript_native": "",  # Empty native transcript
        "transcript_english": "English fallback works",
    }
    setup_mock_response(mock_google_genai_client, json.dumps(response_json))

    result = extract_post_text([Path("dummy.jpg")])

    assert result["transcript_native"] == "English fallback works"
    assert result["title"] == "New Post Processed"  # Testing default


@patch("pathlib.Path.open", new_callable=mock_open, read_data=b"image bytes")
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_no_english_transcript(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text when no English transcript is available."""
    # Both missing
    setup_mock_response(mock_google_genai_client, '{"transcript_english": ""}')

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(
        RuntimeError, match="AI could not extract readable text"
    ):
        extract_post_text([Path("dummy.jpg")])


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_empty_response(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text when AI returns empty response."""
    setup_mock_response(mock_google_genai_client, "")

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(
        RuntimeError, match="AI returned empty post text response"
    ):
        extract_post_text([Path("dummy.jpg")])


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_invalid_json_response(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text when AI returns invalid JSON response."""
    setup_mock_response(
        mock_google_genai_client, "Garbage text without any braces"
    )

    mock_key_manager.key_count = 1
    valid_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else "dummy_key"
    mock_key_manager.get_client.return_value = (
        valid_key,
        mock_google_genai_client,
    )

    with pytest.raises(
        RuntimeError, match="AI returned invalid post text JSON"
    ):
        extract_post_text([Path("dummy.jpg")])


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_quota_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text handles quota errors."""
    error_resp = MagicMock(text="RESOURCE_EXHAUSTED quota")
    error_mock = ClientError("RESOURCE_EXHAUSTED", response=error_resp)
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    mock_key_manager.key_count = 1
    mock_key_manager.get_client.return_value = (
        "key1",
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="All Gemini keys exhausted"):
        extract_post_text([Path("dummy.jpg")])

    mock_key_manager.cooldown_key.assert_called_once_with("key1")


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_invalid_key_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text handles invalid key errors."""
    error_resp = MagicMock(text="API_KEY_INVALID")
    error_mock = ClientError("API_KEY_INVALID", response=error_resp)
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    mock_key_manager.key_count = 1
    mock_key_manager.get_client.return_value = (
        "key1",
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="All Gemini keys exhausted"):
        extract_post_text([Path("dummy.jpg")])

    mock_key_manager.disable_key.assert_called_once_with("key1")


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("core.services.post_gemini.KEY_MANAGER")
def test_extract_post_text_general_error(
    mock_key_manager, _mock_file, mock_google_genai_client
):
    """Test extracting post text handles general errors."""
    error_resp = MagicMock(text="General API Fault")
    error_mock = ClientError("Fault", response=error_resp)
    mock_google_genai_client.models.generate_content.side_effect = error_mock

    mock_key_manager.key_count = 1
    mock_key_manager.get_client.return_value = (
        "key1",
        mock_google_genai_client,
    )

    with pytest.raises(RuntimeError, match="Post text extraction failed"):
        extract_post_text([Path("dummy.jpg")])
