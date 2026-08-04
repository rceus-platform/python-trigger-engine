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
            '{"title": "Mock Title", "hashtags": "#mock #test", "caption": "Mock Caption"}'
        )
        mock_client_instance.models.generate_content.return_value = mock_response

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
def mock_gemini_keys_if_empty():
    """Ensure tests have mock Gemini keys and fresh client pools for every test."""
    from trigger_engine.core import constants
    from trigger_engine.core.services import gemini_transcriber, post_vision_analyzer

    orig_keys = list(constants.GEMINI_API_KEYS)
    if not orig_keys:
        constants.GEMINI_API_KEYS.append("dummy_test_key")

    # Clear cached client instances so each test binds to active mocks
    gemini_transcriber.KEY_MANAGER._clients.clear()
    gemini_transcriber.KEY_MANAGER._cooldowns.clear()
    gemini_transcriber.KEY_MANAGER._index = 0
    gemini_transcriber.KEY_MANAGER._keys = list(constants.GEMINI_API_KEYS)
    for k in gemini_transcriber.KEY_MANAGER._keys:
        gemini_transcriber.KEY_MANAGER._cooldowns[k] = 0.0

    post_vision_analyzer.KEY_MANAGER._clients.clear()
    post_vision_analyzer.KEY_MANAGER._cooldowns.clear()
    post_vision_analyzer.KEY_MANAGER._index = 0
    post_vision_analyzer.KEY_MANAGER._keys = list(constants.GEMINI_API_KEYS)
    for k in post_vision_analyzer.KEY_MANAGER._keys:
        post_vision_analyzer.KEY_MANAGER._cooldowns[k] = 0.0

    yield

    gemini_transcriber.KEY_MANAGER._clients.clear()
    gemini_transcriber.KEY_MANAGER._cooldowns.clear()
    gemini_transcriber.KEY_MANAGER._index = 0

    post_vision_analyzer.KEY_MANAGER._clients.clear()
    post_vision_analyzer.KEY_MANAGER._cooldowns.clear()
    post_vision_analyzer.KEY_MANAGER._index = 0

    if not orig_keys:
        constants.GEMINI_API_KEYS.clear()
        gemini_transcriber.KEY_MANAGER._keys.clear()
        post_vision_analyzer.KEY_MANAGER._keys.clear()
