"""Global pytest fixtures and configuration."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_google_genai_client():
    """Globally mocks the GenAI client and its generate_content method."""
    with patch("google.genai.Client") as MockClient:
        mock_client_instance = MockClient.return_value

        # Mock the generation response
        mock_response = MagicMock()
        mock_response.text = (
            '{"title": "Mock Title", "hashtags": "#mock #test", '
            '"caption": "Mock Caption"}'
        )
        mock_client_instance.models.generate_content.return_value = (
            mock_response
        )

        yield mock_client_instance


@pytest.fixture(autouse=True)
def mock_deepgram_client():
    """Globally mocks the Deepgram SDK client."""
    with patch("deepgram.Deepgram") as MockClient:
        mock_client_instance = MockClient.return_value

        # Mock transcription response
        mock_response = MagicMock()
        mock_response.to_json.return_value = (
            '{"results": {"channels": [{"alternatives": [{"transcript": '
            '"mock transcript from deepgram"}]}]}}'
        )
        mock_client_instance.listen.rest.v.analyze_file.return_value = (
            mock_response
        )

        yield mock_client_instance


@pytest.fixture(autouse=True)
def mock_instaloader():
    """Globally mocks Instaloader to prevent real Instagram scraping."""
    with patch("instaloader.Instaloader") as MockInstaloader:
        mock_instance = MockInstaloader.return_value
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_post_loader():
    """Globally mocks instaloader.Post.from_shortcode."""
    with patch("instaloader.Post.from_shortcode") as mock_post:
        # Create a fake post object
        fake_post = MagicMock()
        fake_post.is_video = True
        fake_post.video_url = "http://mock-video-url.com/video.mp4"
        fake_post.caption = "This is a mock caption for the reel"
        fake_post.owner_username = "mockuser"
        mock_post.return_value = fake_post
        yield mock_post


@pytest.fixture(autouse=True)
def mock_curl_cffi_requests():
    """Globally mocks curl_cffi.requests.Session."""
    with patch("curl_cffi.requests.Session.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"mock video binary data"
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture(autouse=True)
def mock_django_send_mail():
    """Globally mocks Django's built in send_mail function."""
    with patch("django.core.mail.send_mail") as mock_send_mail:
        yield mock_send_mail


@pytest.fixture(autouse=True)
def mock_django_q_async_task():
    """Globally mocks django_q.tasks.async_task to prevent bg execution."""
    with patch("django_q.tasks.async_task") as mock_async_task:
        yield mock_async_task
