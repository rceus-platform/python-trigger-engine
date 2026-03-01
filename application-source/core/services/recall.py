"""Utility helpers to surface recall behavior triggers."""

from datetime import timedelta

from django.utils.timezone import now

from core.models import ReelInsight


def get_daily_triggers(limit: int = 5) -> list[ReelInsight]:
    """Collect the freshest unique ReelInsights for the daily email."""
    today = now()
    collected_insights = []
    seen_ids = set()

    # Priority buckets (new → old)
    buckets = [
        (today - timedelta(days=2), 3),  # last 2 days → pick up to 3
        (today - timedelta(days=7), 2),  # last week → pick up to 2
        (today - timedelta(days=30), 1),  # last month → pick 1
    ]

    for since, max_count in buckets:
        if len(collected_insights) >= limit:
            break

        manager = getattr(ReelInsight, "objects")
        insights = (
            manager.filter(created_at__gte=since).exclude(id__in=seen_ids).order_by("?")
        )

        added_from_bucket = 0
        for insight in insights:
            if added_from_bucket >= max_count or len(collected_insights) >= limit:
                break

            # Ensure it actually has triggers
            if insight.triggers and insight.triggers.strip():
                collected_insights.append(insight)
                seen_ids.add(insight.id)
                added_from_bucket += 1

    return collected_insights[:limit]
