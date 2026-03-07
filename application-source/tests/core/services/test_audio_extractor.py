"""Tests for the audio_extractor service."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.services.audio_extractor import (
    extract_audio_for_gemini,
    get_ffmpeg_path,
)


def test_get_ffmpeg_path_success():
    """Test get_ffmpeg_path returns correct path on success."""
    with patch("shutil.which", return_value="/usr/local/bin/ffmpeg"):
        path = get_ffmpeg_path()
        assert path == "/usr/local/bin/ffmpeg"


def test_get_ffmpeg_path_not_found():
    """Test get_ffmpeg_path raises RuntimeError when ffmpeg is not found."""
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            get_ffmpeg_path()


@patch(
    "core.services.audio_extractor.get_ffmpeg_path",
    return_value="/usr/bin/ffmpeg",
)
@patch("subprocess.run")
def test_extract_audio_for_gemini_success(mock_run, _mock_get_path):
    """Test successful audio extraction."""
    video_path = Path("/tmp/video.mp4")

    # Simulate successful subprocess run
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

    result_path = extract_audio_for_gemini(video_path)

    assert result_path == Path("/tmp/video.mp3")
    mock_run.assert_called_once()

    args, kwargs = mock_run.call_args
    command = args[0]

    # Assert ffmpeg arguments are constructed correctly
    assert command[0] == "/usr/bin/ffmpeg"
    assert command[3] == "/tmp/video.mp4"
    assert command[-1] == "/tmp/video.mp3"
    assert kwargs.get("check") is True


@patch(
    "core.services.audio_extractor.get_ffmpeg_path",
    return_value="/usr/bin/ffmpeg",
)
@patch("subprocess.run")
def test_extract_audio_for_gemini_failure(mock_run, _mock_get_path):
    """Test audio extraction failure handling."""
    video_path = Path("/tmp/video.mp4")

    # Simulate a subprocess failure
    process_error = subprocess.CalledProcessError(
        returncode=1,
        cmd=["ffmpeg"],
        output="Standard out text",
        stderr="Standard error text",
    )
    mock_run.side_effect = process_error

    with pytest.raises(RuntimeError, match="ffmpeg failed") as excinfo:
        extract_audio_for_gemini(video_path)

    assert "Standard out text" in str(excinfo.value)
    assert "Standard error text" in str(excinfo.value)
