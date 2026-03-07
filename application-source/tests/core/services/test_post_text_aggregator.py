"""Tests for the post text aggregator service."""

# pylint: disable=unspecified-encoding

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.services.post_text_aggregator import (
    _extract_shortcode,
    download_instagram_post,
)


def test_extract_shortcode_valid_url():
    """Test standard extraction of shortcode from valid URLs."""
    assert _extract_shortcode("https://instagram.com/p/ABCDEFG/") == "ABCDEFG"
    assert (
        _extract_shortcode("https://instagram.com/p/123456?igshid=xyz")
        == "123456"
    )


def test_extract_shortcode_invalid_url():
    """Test extracting shortcode from an empty URL raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Invalid Instagram post URL"):
        _extract_shortcode("")


@patch("core.services.post_text_aggregator._download_image")
@patch("instaloader.Instaloader")
@patch("instaloader.Post.from_shortcode")
def test_download_instagram_post_single_image(
    mock_from_shortcode, _mock_loader, mock_download
):
    """Test downloading a post with a single image."""
    # Setup mock post
    mock_post = MagicMock()
    mock_post.typename = "GraphImage"
    mock_post.is_video = False
    mock_from_shortcode.return_value = mock_post

    # Setup mock download return path
    expected_path = Path("/tmp/mock_image.jpg")
    mock_download.return_value = expected_path

    paths = download_instagram_post("https://instagram.com/p/SHORTCODE/")

    assert paths == [expected_path]
    mock_download.assert_called_once()


@patch("core.services.post_text_aggregator._download_image")
@patch("instaloader.Instaloader")
@patch("instaloader.Post.from_shortcode")
def test_download_instagram_post_sidecar(
    mock_from_shortcode, _mock_loader, mock_download
):
    """Test downloading a sidecar post containing images and videos."""
    # Setup mock post with multiple nodes
    mock_post = MagicMock()
    mock_post.typename = "GraphSidecar"

    node1 = MagicMock(is_video=False)
    node2 = MagicMock(is_video=True)  # Should be skipped
    node3 = MagicMock(is_video=False)

    mock_post.get_sidecar_nodes.return_value = [node1, node2, node3]
    mock_from_shortcode.return_value = mock_post

    # Setup mock download return path
    mock_download.side_effect = [Path("/tmp/img1.jpg"), Path("/tmp/img3.jpg")]

    paths = download_instagram_post("https://instagram.com/p/SHORTCODE/")

    assert len(paths) == 2
    assert mock_download.call_count == 2


@patch("instaloader.Instaloader")
@patch("instaloader.Post.from_shortcode")
@patch("requests.get")
@patch("pathlib.Path.write_bytes")
def test_download_instagram_post_fallback_success(
    mock_write, mock_get, mock_from_shortcode, _mock_loader
):
    """Test fallback image fetching when instaloader fails."""
    # Force instaloader to fail
    mock_from_shortcode.side_effect = Exception("Instaloader failed")

    # Setup first requests.get (HTML page)
    mock_html_resp = MagicMock()
    mock_html_resp.text = (
        '<html><head><meta property="og:image" '
        'content="http://fallback.com/img.jpg" /></head></html>'
    )

    # Setup second requests.get (Image download)
    mock_img_resp = MagicMock()
    mock_img_resp.content = b"mock image data"

    # Return html first, then image
    mock_get.side_effect = [mock_html_resp, mock_img_resp]

    paths = download_instagram_post("https://instagram.com/p/SHORTCODE/")

    assert len(paths) == 1
    assert "SHORTCODE_fallback.jpg" in str(paths[0])
    mock_write.assert_called_once_with(b"mock image data")


@patch("instaloader.Instaloader")
@patch("instaloader.Post.from_shortcode")
@patch("requests.get")
def test_download_instagram_post_total_failure(
    mock_get, mock_from_shortcode, _mock_loader
):
    """Test behaviour when both Instaloader and fallback fail."""
    # Force instaloader to fail
    mock_from_shortcode.side_effect = Exception("Instaloader failed")

    # Force fallback to fail
    mock_get.side_effect = Exception("Network error")

    with pytest.raises(
        RuntimeError, match="Both Instaloader and fallback failed"
    ):
        download_instagram_post("https://instagram.com/p/SHORTCODE/")


@patch("instaloader.Instaloader")
@patch("instaloader.Post.from_shortcode")
def test_download_instagram_post_no_images(mock_from_shortcode, _mock_loader):
    """Test behaviour when the post lacks valid images."""
    # Setup post with no images (e.g. only video)
    mock_post = MagicMock()
    mock_post.typename = "GraphVideo"
    mock_post.is_video = True
    mock_from_shortcode.return_value = mock_post

    with pytest.raises(
        RuntimeError, match="Instagram post has no downloadable images"
    ):
        download_instagram_post("https://instagram.com/p/SHORTCODE/")


def test_extract_shortcode_invalid():
    """Test extracting shortcode with just whitespace fails."""
    with pytest.raises(RuntimeError, match="Invalid Instagram post URL"):
        _extract_shortcode("    ")


@patch("core.services.post_text_aggregator.instaloader.Instaloader")
@patch("core.services.post_text_aggregator.requests.get")
def test_download_instagram_post_fallback_no_match(mock_get, mock_instaloader):
    """Test fallback failure due to missing og:image tag."""
    # Make instaloader fail
    mock_instance = mock_instaloader.return_value
    mock_instance.context._session.send = MagicMock()

    with patch(
        "core.services.post_text_aggregator.instaloader.Post.from_shortcode",
        side_effect=Exception("Instaloader Fail"),
    ):
        # Mock successful request but missing og:image tag
        mock_response = MagicMock()
        mock_response.text = "<html><body>No image here!</body></html>"
        mock_get.return_value = mock_response

        with pytest.raises(
            RuntimeError,
            match="Both Instaloader and fallback failed for post fail",
        ):
            download_instagram_post("https://instagram.com/p/fail/")


@patch("core.services.post_text_aggregator.instaloader.Instaloader")
@patch("core.services.post_text_aggregator.requests.get")
def test_download_instagram_post_fallback_download_fail(
    mock_get, mock_instaloader, tmp_path
):
    """Test fallback image fetching fails during actual content download."""
    # Make instaloader fail
    mock_instance = mock_instaloader.return_value
    mock_instance.context._session.send = MagicMock()

    with patch(
        "core.services.post_text_aggregator.instaloader.Post.from_shortcode",
        side_effect=Exception("Instaloader Fail"),
    ):
        with patch("core.services.post_text_aggregator.MEDIA_DIR", tmp_path):
            # Mock initial page request success, but inner image download fails
            mock_page_response = MagicMock()
            mock_page_response.text = (
                '<html><meta property="og:image" '
                'content="https://img.com/fall.jpg"></html>'
            )

            mock_img_response = MagicMock()
            mock_img_response.raise_for_status.side_effect = Exception(
                "404 Image Not Found"
            )

            mock_get.side_effect = [mock_page_response, mock_img_response]

            with pytest.raises(
                RuntimeError, match="Both Instaloader and fallback failed"
            ):
                download_instagram_post("https://instagram.com/p/fail/")


@patch("core.services.post_text_aggregator.instaloader.Instaloader")
def test_download_instagram_post_video_carousel_skips(
    mock_instaloader, tmp_path
):
    """Test videos inside sidecars are correctly skipped during download."""
    mock_instance = mock_instaloader.return_value
    mock_instance.context._session.send = MagicMock()

    with patch(
        "core.services.post_text_aggregator.instaloader.Post.from_shortcode"
    ) as mock_from_shortcode:
        with patch("core.services.post_text_aggregator.MEDIA_DIR", tmp_path):
            mock_post = MagicMock()
            mock_post.typename = "GraphSidecar"

            # Node 1 is a video (skipped), Node 2 is an image (downloaded)
            mock_node_video = MagicMock(is_video=True)
            mock_node_image = MagicMock(
                is_video=False, display_url="http://image"
            )
            mock_post.get_sidecar_nodes.return_value = iter(
                [mock_node_video, mock_node_image]
            )
            mock_from_shortcode.return_value = mock_post

            def _fake_download(stem, _url, _date):
                path = Path(str(stem) + ".jpg")
                path.write_text(
                    "fake", encoding="utf-8"
                )  # pylint: disable=unspecified-encoding

            mock_instance.download_pic.side_effect = _fake_download

            paths = download_instagram_post("https://instagram.com/p/multi/")

            assert len(paths) == 1
            assert paths[0].name.endswith("_1.jpg")  # Second index (1)
