"""Send daily recall emails to the configured distribution list."""

from django.template.loader import render_to_string
from django.utils import timezone

from core.services.email_utils import build_daily_email
from core.services.recall import get_daily_triggers


def send_daily_recall_email():
    """Send the daily recall email, returning True when something was sent."""
    insights = get_daily_triggers(limit=1)

    if not insights:
        return False

    today = timezone.localdate().isoformat()
    subject = f"TRIGGER ENGINE: Daily Recall ({today})"

    text_parts = ["Here is your daily recall reel:", ""]
    for insight in insights:
        heading = insight.title or "Reel"
        text_parts.append(f"{heading} ({insight.original_language})")
        text_parts.append(f"Source: {insight.source_url}")
        text_parts.append("Triggers:")
        for t in insight.triggers.splitlines():
            if t.strip():
                text_parts.append(f"- {t.strip()}")
        text_parts.append("")

    text_body = "\n".join(text_parts)

    html_body = render_to_string(
        "emails/daily_recall.html",
        {
            "date": today,
            "insights": insights,
        },
    )

    email = build_daily_email(subject, text_body)

    email.attach_alternative(html_body, "text/html")
    email.send()

    return True
