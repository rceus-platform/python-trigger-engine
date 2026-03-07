"""Tests for the email_error service."""

from unittest.mock import MagicMock, patch

from core.services.email_error import send_error_email


@patch("core.services.email_error.EmailMessage")
def test_send_error_email_success(mock_email_message):
    """Test standard success of send_error_email."""
    mock_email_instance = MagicMock()
    mock_email_message.return_value = mock_email_instance

    with (
        patch("core.services.email_error.EMAIL_HOST_USER", "sender@test.com"),
        patch("core.services.email_error.ADMIN_EMAILS", ["admin@test.com"]),
    ):
        send_error_email("http://example.com/bad", "ValueError", "Trace text")

    mock_email_message.assert_called_once()
    kwargs = mock_email_message.call_args[1]

    assert "TRIGGER ENGINE ERROR" in kwargs["subject"]
    assert "http://example.com/bad" in kwargs["subject"]
    assert "http://example.com/bad" in kwargs["body"]
    assert "ValueError" in kwargs["body"]
    assert "Trace text" in kwargs["body"]
    assert kwargs["from_email"] == "sender@test.com"
    assert kwargs["to"] == ["admin@test.com"]

    mock_email_instance.send.assert_called_once_with(fail_silently=False)


@patch("core.services.email_error.EmailMessage")
def test_send_error_email_exception_safety(mock_email_message):
    """Test send_error_email handles exceptions safely."""
    mock_email_instance = MagicMock()
    mock_email_instance.send.side_effect = Exception("SMTP Auth Failed")
    mock_email_message.return_value = mock_email_instance

    # Even if sending fails, it should be caught and logged safely without
    # raising
    send_error_email("http://example.com/bad", "LocalErr", "Trace")
    mock_email_instance.send.assert_called_once()
