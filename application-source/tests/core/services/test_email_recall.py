"""Tests for the email_recall service."""

from unittest.mock import MagicMock, patch

import pytest

from core.models import ReelInsight
from core.services.email_recall import send_daily_recall_email

pytestmark = pytest.mark.django_db


@patch("core.services.email_recall.get_daily_triggers")
def test_send_daily_recall_email_no_triggers(mock_get_triggers):
    """Test send_daily_recall_email gracefully handles no triggers."""
    mock_get_triggers.return_value = []

    result = send_daily_recall_email()

    assert result is False


@patch("core.services.email_recall.get_daily_triggers")
@patch("core.services.email_recall.build_daily_email")
@patch("core.services.email_recall.render_to_string")
def test_send_daily_recall_email_success(
    mock_render, mock_build, mock_get_triggers
):
    """Test send_daily_recall_email constructs and sends email successfully."""
    mock_get_triggers.return_value = [
        ReelInsight(
            title="Test Reel",
            original_language="en",
            source_url="http://test",
            triggers="t1\n\nt2",
        )
    ]
    mock_render.return_value = "<html>Mock HTML</html>"

    mock_email = MagicMock()
    mock_build.return_value = mock_email

    result = send_daily_recall_email()

    assert result is True

    # Check that builder was called
    assert mock_build.called
    args, _kwargs = mock_build.call_args
    assert "Daily Recall" in args[0]  # subject

    # Check text body formatting
    text_body = args[1]
    assert "Test Reel" in text_body
    assert "t1" in text_body
    assert "t2" in text_body

    # Verify email was sent with HTML part
    mock_email.attach_alternative.assert_called_once_with(
        "<html>Mock HTML</html>", "text/html"
    )
    mock_email.send.assert_called_once()
