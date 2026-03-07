"""Tests for email_utils functions."""

from unittest.mock import MagicMock, mock_open, patch

from django.core.mail import EmailMultiAlternatives

from core.services.email_utils import attach_audio_if_small, build_daily_email


def test_build_daily_email():
    """Test building a daily email instance."""
    email = build_daily_email("Test Subject", "Test Body")
    assert isinstance(email, EmailMultiAlternatives)
    assert email.subject == "Test Subject"
    assert email.body == "Test Body"
    assert "inout440@gmail.com" in email.from_email
    assert "21rhi21@gmail.com" in email.to


def test_attach_audio_if_small_none():
    """Test attach_audio_if_small when path is None."""
    assert attach_audio_if_small(MagicMock(), None) is False


def test_attach_audio_if_small_missing():
    """Test attach_audio_if_small when file does not exist."""
    with patch("os.path.exists", return_value=False):
        assert attach_audio_if_small(MagicMock(), "missing.mp3") is False


def test_attach_audio_if_small_too_large():
    """Test attach_audio_if_small when file exceeds size limit."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=(20 * 1024 * 1024) + 1),
    ):
        assert attach_audio_if_small(MagicMock(), "big.mp3") is False


@patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=100)
@patch(
    "core.services.email_utils.guess_type", return_value=("audio/mpeg", None)
)
def test_attach_audio_if_small_success(
    _mock_guess, _mock_size, _mock_exists, _mock_file
):
    """Test successful audio attachment."""
    email_mock = MagicMock()

    assert attach_audio_if_small(email_mock, "/tmp/small.mp3") is True

    email_mock.attach.assert_called_once_with(
        filename="small.mp3", content=b"fake audio data", mimetype="audio/mpeg"
    )


@patch("builtins.open", side_effect=OSError("Permission denied"))
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=100)
def test_attach_audio_if_small_oserror(_mock_size, _mock_exists, _mock_file):
    """Test handling OSError while reading the audio file."""
    email_mock = MagicMock()
    assert attach_audio_if_small(email_mock, "/tmp/locked.mp3") is False
