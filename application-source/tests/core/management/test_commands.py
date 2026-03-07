"""Tests for management commands."""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command


def test_send_daily_recall_success():
    """Test standard success of send_daily_recall."""
    out = StringIO()
    with patch(
        "core.management.commands.send_daily_recall.send_daily_recall_email",
        return_value=True,
    ):
        call_command("send_daily_recall", stdout=out)
        assert "Daily recall email sent" in out.getvalue()


def test_send_daily_recall_none():
    """Test send_daily_recall when no triggers to send."""
    out = StringIO()
    with patch(
        "core.management.commands.send_daily_recall.send_daily_recall_email",
        return_value=False,
    ):
        call_command("send_daily_recall", stdout=out)
        assert "No triggers to send" in out.getvalue()


def test_cleanup_media_dir_missing(tmp_path):
    """Test cleanup_media handles missing MEDIA_DIR gracefully."""
    out = StringIO()
    with patch(
        "core.management.commands.cleanup_media.MEDIA_DIR",
        tmp_path / "missing",
    ):
        call_command("cleanup_media", stdout=out)
        assert out.getvalue() == ""


def test_cleanup_media(tmp_path):
    """Test cleanup_media deletes correctly based on age."""
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create an old file
    old_file = media_dir / "old.mp4"
    old_file.write_text("old")

    # Create a new file
    new_file = media_dir / "new.mp4"
    new_file.write_text("new")

    out = StringIO()

    # We patch time.time() and the stat().st_mtime property directly
    # A cleaner way is to mock MEDIA_DIR.iterdir to return files with specific
    # st_mtime.

    mock_old = MagicMock(spec=Path)
    mock_old.is_file.return_value = True
    mock_old.name = "old.mp4"
    mock_old_stat = MagicMock()
    mock_old_stat.st_mtime = 1000  # old timestamp
    mock_old.stat.return_value = mock_old_stat

    mock_new = MagicMock(spec=Path)
    mock_new.is_file.return_value = True
    mock_new.name = "new.mp4"
    mock_new_stat = MagicMock()
    mock_new_stat.st_mtime = 9000  # new timestamp
    mock_new.stat.return_value = mock_new_stat

    # Mocking media_dir.iterdir to return our two mocks
    media_dir_mock = MagicMock(spec=Path)
    media_dir_mock.exists.return_value = True
    media_dir_mock.iterdir.return_value = [mock_old, mock_new]

    with patch(
        "core.management.commands.cleanup_media.MEDIA_DIR", media_dir_mock
    ):
        with patch(
            "core.management.commands.cleanup_media.time.time",
            return_value=5000,
        ):
            # The exact time logic: age = now - st_mtime > 3600
            # For old: age = 5000 - 1000 = 4000 > 3600 -> DELETED
            # For new: age = 5000 - 9000 = -4000 < 3600 -> NOT DELETED
            call_command("cleanup_media", stdout=out)

    # Verify unlinks
    mock_old.unlink.assert_called_once()
    mock_new.unlink.assert_not_called()
    assert "Deleted old.mp4" in out.getvalue()
