from datetime import timedelta

from django.utils.timezone import now

from core.models import ReelInsight


def get_daily_triggers(limit: int = 5) -> list[str]:
    today = now()
    collected = []

    # Priority buckets (new → old)
    buckets = [
        (today - timedelta(days=2), 3),  # last 2 days → pick up to 3
        (today - timedelta(days=7), 2),  # last week → pick up to 2
        (today - timedelta(days=30), 1),  # last month → pick 1
    ]

    for since, max_count in buckets:
        if len(collected) >= limit:
            break

        insights = (
            ReelInsight.objects.filter(created_at__gte=since)
            .order_by("-created_at")
            .values_list("triggers", flat=True)
        )

        for block in insights:
            for t in block.splitlines():
                t = t.strip()
                if t and t not in collected:
                    collected.append(t)
                    if len(collected) >= limit or len(collected) >= max_count:
                        break

    return collected[:limit]
