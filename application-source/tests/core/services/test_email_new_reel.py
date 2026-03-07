"""Tests for the email_new_reel service."""

from unittest.mock import MagicMock, mock_open, patch

from django.core.mail import EmailMultiAlternatives

from core.services.email_new_reel import send_new_reel_email
from core.services.email_utils import attach_audio_if_small, build_daily_email


def test_build_daily_email():
    """Test generating a daily email object."""
    with (
        patch("core.services.email_utils.EMAIL_HOST_USER", "sender@test.com"),
        patch(
            "core.services.email_utils.DAILY_RECALL_EMAILS",
            ["receiver@test.com"],
        ),
    ):
        email = build_daily_email("Test Subject", "Hello World")

        assert isinstance(email, EmailMultiAlternatives)
        assert email.subject == "Test Subject"
        assert email.body == "Hello World"
        assert email.from_email == "sender@test.com"
        assert email.to == ["receiver@test.com"]


@patch("os.path.exists", return_value=False)
def test_attach_audio_if_small_not_exists(_mock_exists):
    """Test attach_audio_if_small handles missing files."""
    email = MagicMock()
    assert not attach_audio_if_small(email, "/fake/audio.mp3")


@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=25 * 1024 * 1024)  # 25MB
def test_attach_audio_if_small_too_large(_mock_size, _mock_exists):
    """Test attach_audio_if_small rejects oversized files."""
    email = MagicMock()
    # Should fail because > 20MB
    assert not attach_audio_if_small(email, "/fake/huge.mp3")


@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=5 * 1024 * 1024)  # 5MB
@patch(
    "core.services.email_utils.guess_type", return_value=("audio/mpeg", None)
)
@patch("builtins.open", new_callable=mock_open, read_data=b"audio bytes")
def test_attach_audio_if_small_success(
    _mock_file, _mock_guess, _mock_size, _mock_exists
):
    """Test successful audio attachment."""
    email = MagicMock()
    assert attach_audio_if_small(email, "/fake/small.mp3")

    email.attach.assert_called_once_with(
        filename="small.mp3", content=b"audio bytes", mimetype="audio/mpeg"
    )


@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=5 * 1024 * 1024)  # 5MB
@patch("builtins.open")
def test_attach_audio_if_small_ioerror(mock_file, _mock_size, _mock_exists):
    """Test handling IO errors during audio attachment."""
    mock_file.side_effect = IOError("Permissions denied")
    email = MagicMock()
    assert not attach_audio_if_small(email, "/fake/small.mp3")


@patch("core.services.email_new_reel.build_daily_email")
@patch("core.services.email_new_reel.render_to_string")
@patch("core.services.email_new_reel.attach_audio_if_small")
def test_send_new_reel_email_success(
    mock_attach_audio, mock_render, mock_build
):
    """Test successful sending of a new reel email."""
    # Mock models and functions
    insight = MagicMock()
    insight.title = "A Great Reel"
    insight.triggers = "Trigger 1\nTrigger 2"

    mock_email = MagicMock()
    mock_build.return_value = mock_email
    mock_render.return_value = "<html>Html Body</html>"
    mock_attach_audio.return_value = True

    send_new_reel_email(insight, "/path/to/audio.mp3")

    # Assertions
    mock_build.assert_called_once()
    args, _kwargs = mock_build.call_args
    assert args[0] == "TRIGGER ENGINE: A Great Reel"
    assert "A new reel was processed" in args[1]
    assert "- Trigger 1" in args[1]

    mock_attach_audio.assert_called_once_with(mock_email, "/path/to/audio.mp3")
    mock_render.assert_called_once()

    mock_email.attach_alternative.assert_called_once_with(
        "<html>Html Body</html>", "text/html"
    )
    mock_email.send.assert_called_once()


@patch("core.services.email_new_reel.build_daily_email")
@patch("core.services.email_new_reel.render_to_string")
def test_send_new_reel_email_no_audio(mock_render, mock_build):
    """Test sending new reel email with no audio attached."""
    insight = MagicMock()
    insight.title = None  # Fallback check
    insight.triggers = "Trigger 1"

    mock_email = MagicMock()
    mock_build.return_value = mock_email

    send_new_reel_email(insight, None)

    args, _kwargs = mock_build.call_args
    # Testing fallback title
    assert args[0] == "TRIGGER ENGINE: New Reel Processed"

    # Check that it renders with audio_attached=False
    args, _kwargs = mock_render.call_args
    assert args[1]["audio_attached"] is False
    mock_email.send.assert_called_once()
