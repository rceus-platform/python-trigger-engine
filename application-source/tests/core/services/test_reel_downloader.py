"""Tests for the reel_downloader service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.services.reel_downloader import (
    MEDIA_DIR,
    _download_file,
    _extract_shortcode,
    _extract_values_by_key,
    download_reel,
    get_reel_metadata,
)


def test_extract_shortcode_valid():
    """Test extracting shortcode from valid reel URL."""
    assert (
        _extract_shortcode("https://instagram.com/reel/AaBbCcDd/")
        == "AaBbCcDd"
    )
    assert _extract_shortcode("https://instagram.com/p/123456/") == "123456"


def test_extract_shortcode_invalid():
    """Test extracting shortcode handles invalid URLs."""
    with pytest.raises(ValueError, match="Cannot extract shortcode from"):
        _extract_shortcode("https://instagram.com/tv/")


def test_extract_shortcode_malformed():
    """Test extracting shortcode handles malformed URLs."""
    with pytest.raises(
        ValueError, match="Cannot extract shortcode from: http://invalid"
    ):
        _extract_shortcode("http://invalid")


def test_extract_values_by_key_basic():
    """Test extracting nested values by key."""
    data = {
        "a": "target_val",
        "b": {"a": "target_val_nested"},
        "c": [{"a": "target_val_list"}],
    }

    assert _extract_values_by_key(data, "a") == [
        "target_val",
        "target_val_nested",
        "target_val_list",
    ]


def test_extract_values_by_key_complex():
    """Test extracting complex nested video versions."""
    data = {
        "a": 1,
        "video_versions": [{"url": "val1"}],
        "nested": {"video_versions": [{"url": "val2"}]},
        "list": [{"video_versions": [{"url": "val3"}]}],
    }
    results = _extract_values_by_key(data, "video_versions")
    assert len(results) == 3
    assert results == [[{"url": "val1"}], [{"url": "val2"}], [{"url": "val3"}]]


@patch("requests.get")
@patch("pathlib.Path.mkdir")
@patch("builtins.open")
def test_download_file_mocked(_mock_open, _mock_mkdir, mock_requests_get):
    """Test downloading file handles requests correctly."""
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
    mock_requests_get.return_value = mock_resp

    _download_file("http://cdn.mp4", Path("/tmp/file.mp4"))
    mock_requests_get.assert_called_once_with(
        "http://cdn.mp4", stream=True, timeout=60
    )
    mock_resp.raise_for_status.assert_called_once()
    _mock_open.assert_called_once_with(Path("/tmp/file.mp4"), "wb")


@patch("core.services.reel_downloader.requests.get")
def test_download_file_stream(mock_get, tmp_path):
    """Test downloading file streaming logic directly."""
    # Test _download_file logic directly
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"chunk1", b"chunk2"]
    mock_get.return_value = mock_resp

    target_path = tmp_path / "test.mp4"
    res = _download_file("http://video/file.mp4", target_path)

    assert res == target_path
    assert res.read_bytes() == b"chunk1chunk2"
    mock_resp.raise_for_status.assert_called_once()


@patch("yt_dlp.YoutubeDL")
@patch("pathlib.Path.exists")
def test_get_reel_metadata(mock_exists, mock_ytdl):
    """Test extracting reel metadata using yt-dlp."""
    # Simulate cookies existing
    mock_exists.return_value = True

    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {
        "id": "123",
        "title": "Test Title",
    }

    meta = get_reel_metadata("https://instagram.com/reel/123/")

    assert meta["id"] == "123"
    assert meta["title"] == "Test Title"
    mock_instance.extract_info.assert_called_once_with(
        "https://instagram.com/reel/123/", download=False
    )
    # Check that cookiefile was passed to options since exists() is True
    args, _kwargs = mock_ytdl.call_args
    assert "cookiefile" in args[0]


@patch("yt_dlp.YoutubeDL")
@patch("pathlib.Path.exists")
def test_get_reel_metadata_no_cookies(mock_exists, mock_ytdl):
    """Test extracting reel metadata handles no cookies."""
    mock_exists.return_value = False
    mock_instance = mock_ytdl.return_value.__enter__.return_value
    mock_instance.extract_info.return_value = {}

    get_reel_metadata("https://instagram.com/reel/123/")

    args, _kwargs = mock_ytdl.call_args
    assert "cookiefile" not in args[0]


@patch("core.services.reel_downloader.yt_dlp.YoutubeDL")
@patch("core.services.reel_downloader.Path.exists")
def test_get_reel_metadata_no_cookiefile(mock_exists, mock_ytdl):
    """Test extracting reel metadata directly ignoring missing cookiefile."""
    mock_exists.return_value = False

    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "id": "123",
        "title": "Test Title",
    }
    mock_ytdl.return_value.__enter__.return_value = mock_instance

    metadata = get_reel_metadata("http://reel")

    assert metadata["id"] == "123"
    assert metadata["title"] == "Test Title"


@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_failed_webpage(mock_curl_get):
    """Test handling failed reel webpage."""
    mock_resp = MagicMock(status_code=404)
    mock_curl_get.return_value = mock_resp

    with pytest.raises(RuntimeError, match="Failed to fetch reel page"):
        download_reel("https://instagram.com/reel/ABC/")


@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_403(mock_curl_get):
    """Test handling HTTP 403 on fetching reel webpage."""
    mock_curl_get.return_value.status_code = 403

    with pytest.raises(
        RuntimeError, match="Failed to fetch reel page \\(HTTP 403\\)"
    ):
        download_reel("https://instagram.com/reel/shorty/")


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_json_success(mock_curl_get, mock_download):
    """Test successful reel JSON extraction."""
    mock_resp = MagicMock(status_code=200)
    # Provide a page with the correct embedded json structure inside a script
    # tag
    script_data = json.dumps(
        {"video_versions": [{"url": "http://json_video.mp4"}]}
    )
    mock_resp.text = (
        '<html><body><script type="application/json">'
        f"{script_data}</script></body></html>"
    )
    mock_curl_get.return_value = mock_resp

    expected_path = MEDIA_DIR / "ABC.mp4"
    mock_download.return_value = expected_path

    result = download_reel("https://instagram.com/reel/ABC/")

    assert result == expected_path
    mock_download.assert_called_once_with(
        "http://json_video.mp4", expected_path
    )


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_json_success_alternative(mock_curl_get, mock_dl):
    """Test successful reel JSON extraction alternative parsing."""
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = (
        "<html>\n"
        '    <script type="application/json">{"video_versions": '
        '[{"url": "http://json_video"}]}</script>\n'
        "</html>\n"
    )
    mock_dl.return_value = Path("test.mp4")

    assert download_reel("https://instagram.com/reel/shorty/") == Path(
        "test.mp4"
    )
    mock_dl.assert_called_once()
    assert mock_dl.call_args[0][0] == "http://json_video"


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_regex_fallback_success(mock_curl_get, mock_download):
    """Test fallback to regex successful downloading."""
    mock_resp = MagicMock(status_code=200)
    # No useful JSON, but raw html contains a matching CDN url
    mock_curl_get.return_value.text = (
        '<html> "https://instagram.fcow1-2.fna.fbcdn.net/'
        'v/test/video.mp4xyz" </html>'
    )
    mock_curl_get.return_value = mock_resp

    expected_path = MEDIA_DIR / "ABC.mp4"
    mock_download.return_value = expected_path

    result = download_reel("https://instagram.com/reel/ABC/")

    assert result == expected_path
    mock_download.assert_called_once()
    args, _ = mock_download.call_args
    assert "video.mp4" in args[0]


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_regex_success(mock_curl_get, mock_dl):
    """Test direct regex matching success."""
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = """
    <html>
        <!-- No JSON here -->
        "https://instagram.fxxx.mp4?abc"
    </html>
    """
    mock_dl.return_value = Path("test_regex.mp4")

    assert download_reel("https://instagram.com/reel/shorty/") == Path(
        "test_regex.mp4"
    )
    mock_dl.assert_called_once()
    assert mock_dl.call_args[0][0] == "https://instagram.fxxx.mp4?abc"


@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_complete_failure(mock_curl_get):
    """Test downloading completely missing any json/regex data."""
    mock_resp = MagicMock(status_code=200)
    # Blank page, no json, no regex match
    mock_resp.text = "<html><body></body></html>"
    mock_curl_get.return_value = mock_resp

    with pytest.raises(
        RuntimeError, match="Could not find a playable video URL"
    ):
        download_reel("https://instagram.com/reel/ABC/")


@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_missing_all(mock_curl_get):
    """Test failed regex and empty page fallback."""
    # No scripts, no Regex match
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = "<html><body>No video here</body></html>"

    with pytest.raises(
        RuntimeError, match="Could not find a playable video URL"
    ):
        download_reel("https://instagram.com/reel/shorty/")


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_invalid_json(mock_curl_get, _mock_dl):
    """Test handling invalid json fallback."""
    # json.loads fails, regex doesn't match
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = (
        "<html>\n"
        '    <script type="application/json">{"video_versions": '
        "bad json format} </script>\n"
        "</html>\n"
    )

    with pytest.raises(
        RuntimeError, match="Could not find a playable video URL"
    ):
        download_reel("https://instagram.com/reel/shorty/")


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_json_empty_video_versions(mock_curl_get, _mock_dl):
    """Test error handling on missing valid json parts."""
    # Valid json but video_versions is empty, regex doesn't match
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = """
    <html>
        <script type="application/json">{"video_versions": []}</script>
    </html>
    """

    with pytest.raises(
        RuntimeError, match="Could not find a playable video URL"
    ):
        download_reel("https://instagram.com/reel/shorty/")


@patch("core.services.reel_downloader._download_file")
@patch("core.services.reel_downloader.curl_requests.get")
def test_download_reel_json_missing_url(mock_curl_get, _mock_dl):
    """Test error handling with missing url string."""
    # Valid json with video_versions but no url key inside
    mock_curl_get.return_value.status_code = 200
    mock_curl_get.return_value.text = (
        "<html>\n"
        '    <script type="application/json">{"video_versions": '
        '[[{"not_url": "xyz"}]]}</script>\n'
        "</html>\n"
    )

    with pytest.raises(
        RuntimeError, match="Could not find a playable video URL"
    ):
        download_reel("https://instagram.com/reel/shorty/")
