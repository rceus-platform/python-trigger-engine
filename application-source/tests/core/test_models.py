"""Tests for the database models."""

import pytest

from core.models import ReelInsight

pytestmark = pytest.mark.django_db


def test_reelinsight_str():
    """Test string representation of the ReelInsight model."""
    insight = ReelInsight(source_url="https://example.com/reel/123")
    assert str(insight) == "https://example.com/reel/123"
