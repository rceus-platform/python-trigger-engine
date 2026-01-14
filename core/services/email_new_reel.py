from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def send_new_reel_email(insight):
    subject = "New Reel Processed"

    text_body = "\n".join(
        [
            "A new reel was processed.",
            "",
            "Triggers:",
            *[f"- {t}" for t in insight.triggers.splitlines()],
        ]
    )

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>New Reel Processed</h2>
        <p><strong>Language:</strong> {insight.original_language}</p>
        <p><strong>Source:</strong> <a href="{insight.source_url}">View Reel</a></p>

        <h3>Triggers</h3>
        <ul>
          {"".join(f"<li>{t}</li>" for t in insight.triggers.splitlines())}
        </ul>

        <hr>
        <p style="font-size:12px;color:#666;">
          Immediate reinforcement.
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
