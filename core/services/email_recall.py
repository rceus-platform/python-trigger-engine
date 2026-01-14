from datetime import date

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from core.services.recall import get_daily_triggers


def send_daily_recall_email():
    triggers = get_daily_triggers(limit=5)

    if not triggers:
        return False

    subject = f"Daily Recall — {date.today().isoformat()}"

    text_body = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(triggers)])

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>Daily Recall</h2>
        <p><strong>{date.today().isoformat()}</strong></p>
        <ol>
          {"".join(f"<li>{t}</li>" for t in triggers)}
        </ol>
        <hr>
        <p style="color:#666;font-size:12px;">
          Read. Apply. Repeat.
        </p>
      </body>
    </html>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.DAILY_RECALL_EMAIL],
    )

    email.attach_alternative(html_body, "text/html")
    email.send()

    return True
