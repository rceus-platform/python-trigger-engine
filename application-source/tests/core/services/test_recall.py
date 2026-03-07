"""Tests for the recall service triggers."""

# pylint: disable=unused-argument,redefined-outer-name

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils.timezone import now

from core.models import ReelInsight
from core.services.recall import get_daily_triggers


@pytest.fixture
def mock_now():
    """Fixture to freeze time to ensure deterministic triggers tests."""
    # Use a fixed time for deterministic tests
    fixed_time = now()
    with patch("core.services.recall.now", return_value=fixed_time):
        yield fixed_time


@pytest.fixture
def base_insights(db, mock_now):  # pylint: disable=unused-argument,redefined-outer-name
    """Fixture to initialize a standard distribution of reel insights."""
    # Bucket 1: Last 2 days
    ReelInsight.objects.create(
        source_url="http://b1-1",
        title="B1-1",
        triggers="Trig1",
        created_at=mock_now - timedelta(days=1),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b1-2",
        title="B1-2",
        triggers="Trig2",
        created_at=mock_now - timedelta(hours=12),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b1-3",
        title="B1-3",
        triggers="Trig3",
        created_at=mock_now - timedelta(hours=2),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b1-4",
        title="B1-4",
        triggers="Trig4",
        created_at=mock_now - timedelta(hours=1),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )  # Should be excluded if bucket limit is 3

    # Bucket 1 invalid (no triggers)
    ReelInsight.objects.create(
        source_url="http://b1-empty",
        title="B1-E",
        triggers="",
        created_at=mock_now - timedelta(hours=5),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )

    # Bucket 2: Last 7 days
    ReelInsight.objects.create(
        source_url="http://b2-1",
        title="B2-1",
        triggers="Trig5",
        created_at=mock_now - timedelta(days=5),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b2-2",
        title="B2-2",
        triggers="Trig6",
        created_at=mock_now - timedelta(days=6),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b2-3",
        title="B2-3",
        triggers="Trig7",
        created_at=mock_now - timedelta(days=4),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )  # Excluded if limit 2

    # Bucket 3: Last 30 days
    ReelInsight.objects.create(
        source_url="http://b3-1",
        title="B3-1",
        triggers="Trig8",
        created_at=mock_now - timedelta(days=20),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )
    ReelInsight.objects.create(
        source_url="http://b3-2",
        title="B3-2",
        triggers="Trig9",
        created_at=mock_now - timedelta(days=25),
        transcript_english="OK",
        original_language="en",
        transcript_original="OK",
    )  # Excluded if limit 1


@pytest.mark.django_db
def test_get_daily_triggers(
    base_insights,
):  # pylint: disable=unused-argument,redefined-outer-name
    """Test getting daily triggers with the default bucket settings."""
    insights = get_daily_triggers(limit=5)

    # Total limit should not be exceeded even if buckets have more
    assert len(insights) <= 5

    # Ensure they all have triggers and are unique
    insight_ids = set()
    for insight in insights:
        assert insight.triggers.strip() != ""
        insight_ids.add(insight.id)

    assert len(insight_ids) == len(insights)  # All unique


@pytest.mark.django_db
def test_get_daily_triggers_short_limit(
    base_insights,
):  # pylint: disable=unused-argument,redefined-outer-name
    """Test getting daily triggers applying a short hard limit globally."""
    insights = get_daily_triggers(limit=2)
    assert len(insights) == 2


@pytest.mark.django_db
def test_get_daily_triggers_empty_db():
    """Test getting daily triggers works safely on an empty database."""
    assert len(get_daily_triggers()) == 0
