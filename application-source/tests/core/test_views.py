"""Tests for API and UI views, and background processing handlers."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import ReelInsight
from core.views import background_process_reel

pytestmark = pytest.mark.django_db


class ErrorEmailTest(TestCase):
    """Test suite for error email sending from background tasks."""

    def setUp(self):
        """Set up test client and targeted URL."""
        self.client = Client()
        self.url = reverse("ui-index") + "api/process-reel/"

    @patch("core.views.download_reel")
    @patch("core.views.send_error_email")
    def test_error_email_sent_on_failure(self, mock_send_email, mock_download):
        """Test error email is sent when background processing fails."""
        # Create a mock insight
        insight = ReelInsight.objects.create(
            source_url="https://www.instagram.com/reel/test/",
            title="Test",
        )

        # Simulate a failure in download_reel
        mock_download.side_effect = Exception("Simulated Download Failure")

        # We need to call background_process_reel directly since the view just
        # enqueues
        background_process_reel(
            insight.pk, "https://www.instagram.com/reel/test/"
        )

        # Verify send_error_email was called
        mock_send_email.assert_called_once()
        kwargs = mock_send_email.call_args.kwargs
        self.assertEqual(kwargs["url"], "https://www.instagram.com/reel/test/")
        self.assertIn("Simulated Download Failure", kwargs["error_message"])


# --- UI / Auth / Simple Endpoints ---


def test_ui_index_unauthenticated(client):
    """Test standard unauthenticated redirection loop for the UI index page."""
    response = client.get(reverse("ui-index"))
    assert response.status_code == 302
    assert response.url == reverse("auth-gateway")


def test_ui_index_authenticated_session(client):
    """Test an authenticated user can hit the UI index page successfully."""
    session = client.session
    session["is_authenticated"] = True
    session.save()
    response = client.get(reverse("ui-index"))
    assert response.status_code == 200


def test_auth_gateway_unauthenticated(client):
    """Test unauthenticated users can access the auth gateway screen."""
    response = client.get(reverse("auth-gateway"))
    assert response.status_code == 200


def test_auth_gateway_authenticated(client):
    """Test authenticated users on auth gateway are redirected back to UI."""
    session = client.session
    session["is_authenticated"] = True
    session.save()
    response = client.get(reverse("auth-gateway"))
    assert response.status_code == 302
    assert response.url == reverse("ui-index")


def test_login_passcode_get(client):
    """Test standard GET rendering of the login pin screen."""
    response = client.get(reverse("login-pin"))
    assert response.status_code == 200


@patch("core.views.settings.SITE_PASSCODE", "1234")
def test_login_passcode_post_success(client):
    """Test validating correct login pin submissions."""
    response = client.post(reverse("login-pin"), {"pin": "1234"})
    assert response.status_code == 302
    assert response.url == reverse("ui-index")
    assert client.session.get("is_authenticated") is True


@patch("core.views.settings.SITE_PASSCODE", "1234")
def test_login_passcode_post_fail(client):
    """Test rejecting wrong pin submissions gracefully without errors."""
    response = client.post(reverse("login-pin"), {"pin": "0000"})
    assert response.status_code == 200
    assert b"Invalid PIN" in response.content


def test_favicon_not_found(client, tmp_path):
    """Test rendering 404 cleanly when favicon file is missing from setup."""
    with patch("core.views.FAVICON_PATH", tmp_path / "missing.png"):
        response = client.get(reverse("favicon"))
        assert response.status_code == 404


def test_favicon_success(client, tmp_path):
    """Test favicon returns proper bytes stream on valid path."""
    fake_png = tmp_path / "favicon.png"
    fake_png.write_bytes(b"fake_image_bytes")
    with patch("core.views.FAVICON_PATH", fake_png):
        response = client.get(reverse("favicon"))
        assert response.status_code == 200
        assert response.content == b"fake_image_bytes"
        assert response["Content-Type"] == "image/png"


# --- Core Process Endpoints ---


def test_check_task_status_not_found(client):
    """Test status polling fails on invalid task ID gracefully."""
    response = client.get("/api/task-status/999/")
    assert response.status_code == 404


def test_check_task_status_processing(client):
    """Test status polling handles an ongoing insight task accurately."""
    insight = ReelInsight.objects.create(source_url="http://test")
    response = client.get(f"/api/task-status/{insight.pk}/")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


def test_check_task_status_complete(client):
    """Test polling returns fully loaded cached document objects securely."""
    insight = ReelInsight.objects.create(
        source_url="http://test",
        title="Valid Title",
        triggers="t1\nt2",
        transcript_original="Native",
        transcript_english="Eng",
        original_language="en",
        processed_at=timezone.now(),
    )
    response = client.get(f"/api/task-status/{insight.pk}/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["title"] == "Valid Title"
    assert data["triggers"] == ["t1", "t2"]


@patch("core.views.get_daily_triggers", return_value=[])
def test_daily_recall(_mock_get_daily, client):
    """Test generating daily recall endpoints empty triggers safely."""
    response = client.get("/api/recall/daily/")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert data["count"] == 0
    assert data["triggers"] == []


# --- Process Reel API ---


def test_process_reel_no_url(client):
    """Test process_reel validating missing payloads efficiently."""
    response = client.post(
        "/api/process-reel/", json.dumps({}), content_type="application/json"
    )
    assert response.status_code == 400
    assert (
        "Valid Instagram URL required" in response.json()["error"]["message"]
    )


def test_process_reel_cache_hit_processed(client):
    """Test process_reel identifying fully cached processed contents safely."""
    insight = ReelInsight.objects.create(
        source_url="https://instagram.com/p/123",
        processed_at=timezone.now(),
        title="Done",
    )
    response = client.post(
        "/api/process-reel/",
        json.dumps({"url": "https://instagram.com/p/123"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cached"
    assert data["id"] == insight.pk


@patch("core.views.async_task")
def test_process_reel_cache_hit_processing_restart(mock_async, client):
    """Test process_reel recovering stuck jobs and rescheduling safely."""
    # Simulate a stuck task that's older than 5 minutes
    past_time = timezone.now() - timezone.timedelta(minutes=6)
    insight = ReelInsight.objects.create(
        source_url="https://instagram.com/p/123", title="Stuck"
    )
    ReelInsight.objects.filter(pk=insight.pk).update(
        created_at=past_time
    )  # bypass auto_now_add

    response = client.post(
        "/api/process-reel/",
        json.dumps({"url": "https://instagram.com/p/123"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["id"] == insight.pk
    # Should restart the async task
    mock_async.assert_called_once_with(
        "core.views.background_process_reel",
        insight.pk,
        "https://instagram.com/p/123",
    )


@patch("core.views.async_task")
@patch("core.views.get_reel_metadata")
def test_process_reel_metadata_source_id_cache(mock_meta, _mock_async, client):
    """Test process_reel cache resolution matching IDs directly safely."""
    # Tests the scenario where URL differs but source_id is the same
    ReelInsight.objects.create(
        source_url="https://instagram.com/reel/abc",
        source_id="12345",
        processed_at=timezone.now(),
        title="From Metadata",
    )
    mock_meta.return_value = {"id": "12345"}

    # Send a different url that shares the same source ID
    response = client.post(
        "/api/process-reel/",
        json.dumps({"url": "https://instagram.com/reel/xyz"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cached"
    assert data["title"] == "From Metadata"


@patch("core.views.async_task")
@patch(
    "core.views.get_reel_metadata", side_effect=Exception("Failed to get meta")
)
def test_process_reel_new_record(_mock_meta, mock_async, client):
    """Test process_reel fully routing valid new jobs out safely."""
    response = client.post(
        "/api/process-reel/",
        json.dumps({"url": "https://instagram.com/reel/newone"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    insight_id = data["id"]

    # Insight should be created
    insight = ReelInsight.objects.get(pk=insight_id)
    assert insight.source_url == "https://instagram.com/reel/newone"

    mock_async.assert_called_once_with(
        "core.views.background_process_reel",
        insight.pk,
        "https://instagram.com/reel/newone",
    )


def test_process_reel_exception(client):
    """Test process_reel failing completely on deeply malformed payloads."""
    # Send invalid JSON to trigger the wide exception catch
    response = client.post(
        "/api/process-reel/", "{badjson:", content_type="application/json"
    )
    assert response.status_code == 500


# --- Background Processing API ---


@patch("core.views.download_instagram_post")
@patch("core.views.extract_post_text")
@patch("core.services.email_new_reel.send_new_reel_email")
def test_background_process_reel_post(
    mock_send_email, mock_extract, mock_download
):
    """Test the complete background pipeline handling posts correctly."""
    insight = ReelInsight.objects.create(
        source_url="https://instagram.com/p/123", title="Pending"
    )

    mock_img_path = MagicMock(spec=Path)
    mock_download.return_value = [mock_img_path]
    mock_extract.return_value = {
        "language": "es",
        "transcript_native": "Hola",
        "transcript_english": "Hello",
        "triggers": ["T1", "T2"],
        "title": "Extracted Post Title",
    }

    background_process_reel(insight.pk, "https://instagram.com/p/123")

    insight.refresh_from_db()
    assert insight.original_language == "es"
    assert insight.transcript_original == "Hola"
    assert insight.title == "Extracted Post Title"
    assert insight.processed_at is not None

    mock_send_email.assert_called_once()
    mock_img_path.unlink.assert_called_once()


@patch("core.views.download_reel")
@patch("core.views.extract_audio_for_gemini")
@patch("core.views.compute_audio_hash")
@patch("core.views.gemini_transcribe")
@patch("core.services.email_new_reel.send_new_reel_email")
def test_background_process_reel_video(
    mock_send_email,
    mock_transcribe,
    mock_hash,
    mock_extract_audio,
    mock_download,
):
    """Test the complete background pipeline handling videos correctly."""
    insight = ReelInsight.objects.create(
        source_url="https://instagram.com/reel/123", title="Pending"
    )

    mock_video_path = MagicMock(spec=Path)
    mock_audio_path = MagicMock(spec=Path)

    mock_download.return_value = mock_video_path
    mock_extract_audio.return_value = mock_audio_path
    mock_hash.return_value = "newhash123"

    mock_transcribe.return_value = {
        "language": "en",
        "transcript_native": "testing",
        "transcript_english": "testing",
        "triggers": ["vT1"],
        "title": "Video Title",
    }

    background_process_reel(insight.pk, "https://instagram.com/reel/123")

    insight.refresh_from_db()
    assert insight.audio_hash == "newhash123"
    assert insight.title == "Video Title"

    mock_send_email.assert_called_once()
    mock_video_path.unlink.assert_called_once()


@patch("core.views.download_reel")
@patch("core.views.extract_audio_for_gemini")
@patch("core.views.compute_audio_hash")
@patch("core.services.email_new_reel.send_new_reel_email")
def test_background_process_reel_duplicate_hash(
    mock_send_email, mock_hash, mock_extract_audio, mock_download
):
    """Test background task copying previous transcription effectively."""
    # Setup existing insight with hash
    ReelInsight.objects.create(
        source_url="https://other",
        audio_hash="samehash456",
        title="Original Video",
        transcript_original="copythis",
        original_language="en",
        transcript_english="engcopy",
        triggers="abc",
        processed_at=timezone.now(),
    )
    insight = ReelInsight.objects.create(
        source_url="https://instagram.com/reel/456", title="Pending"
    )

    mock_video_path = MagicMock(spec=Path)
    mock_audio_path = MagicMock(spec=Path)

    mock_download.return_value = mock_video_path
    mock_extract_audio.return_value = mock_audio_path
    mock_hash.return_value = "samehash456"

    background_process_reel(insight.pk, "https://instagram.com/reel/456")

    insight.refresh_from_db()
    assert (
        insight.audio_hash is None
    )  # Fix in views.py needed so it doesn't duplicate the unique constraint
    assert insight.title == "Original Video"
    assert insight.transcript_original == "copythis"
    assert insight.processed_at is not None

    # We exit early on hash match, so new reel email is not sent in this flow
    # natively
    mock_send_email.assert_not_called()
    mock_video_path.unlink.assert_called_once()
