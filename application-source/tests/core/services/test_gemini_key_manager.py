"""Tests for the gemini_key_manager service."""

from unittest.mock import patch

import pytest

from core.services.gemini_key_manager import GeminiKeyManager


def test_key_manager_initialization():
    """Test basic initialization of the key manager."""
    manager = GeminiKeyManager(keys=["key1", "key2"])
    assert manager.key_count == 2


def test_key_manager_empty_keys():
    """Test error handling when initializing with empty keys."""
    with pytest.raises(RuntimeError, match="No Gemini API keys configured"):
        GeminiKeyManager(keys=[])


@patch("google.genai.Client")
def test_key_manager_get_client_rotation(_mock_client):
    """Test rotation of client API keys."""
    manager = GeminiKeyManager(keys=["key1", "key2"])

    # First call gets key1
    key, _client = manager.get_client()
    assert key == "key1"

    # Second call gets key2
    key, _client = manager.get_client()
    assert key == "key2"

    # Third call wraps back to key1
    key, _client = manager.get_client()
    assert key == "key1"


@patch("google.genai.Client")
def test_key_manager_cooldown(_mock_client):
    """Test key cooldown mechanics."""
    manager = GeminiKeyManager(keys=["key1", "key2"], cooldown_seconds=60)

    # Simulate putting key1 on cooldown
    manager.cooldown_key("key1")

    # Should get key2 since key1 is cooling down
    key, _client = manager.get_client()
    assert key == "key2"

    # If we put key2 on cooldown too, it should raise an exhaustion error
    manager.cooldown_key("key2")

    with pytest.raises(
        RuntimeError, match="All Gemini API keys are exhausted"
    ):
        manager.get_client()


@patch("google.genai.Client")
def test_key_manager_disable(_mock_client):
    """Test mechanism for disabling keys entirely."""
    manager = GeminiKeyManager(keys=["key1", "key2"])

    manager.disable_key("key1")

    # Should get key2
    key, _client = manager.get_client()
    assert key == "key2"

    manager.disable_key("key2")

    with pytest.raises(
        RuntimeError, match="All Gemini API keys are exhausted"
    ):
        manager.get_client()


@patch("google.genai.Client")
def test_next_key_legacy_helper(_mock_client):
    """Test next_key legacy backward compatibility method."""
    manager = GeminiKeyManager(keys=["key1"])
    assert manager.next_key() == "key1"
