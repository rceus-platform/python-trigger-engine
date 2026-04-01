"""Instagram cookie health-check and admin alerting.

Run periodically (e.g. daily via cron) to detect expired or missing
cookies before users hit errors:

    python manage.py check_cookies
"""

import logging
from datetime import datetime, timezone
from http.cookiejar import MozillaCookieJar
from pathlib import Path

from curl_cffi import requests as curl_requests

from core.constants import ADMIN_EMAILS, EMAIL_HOST_USER

logger = logging.getLogger(__name__)

# The critical session cookie — without it, nothing works.
_KEY_COOKIES = ("sessionid", "ds_user_id")


def _cookies_path() -> Path:
    from core.constants import INSTAGRAM_COOKIES_PATH

    return Path(INSTAGRAM_COOKIES_PATH)


def check_cookie_file() -> dict:
    """Inspect the cookie file and return a health report.

    Returns a dict with keys:
      - ok (bool): True if everything looks good
      - missing_file (bool)
      - missing_cookies (list[str]): critical cookies not found
      - expired_cookies (list[str]): critical cookies that are expired
      - days_until_expiry (int | None): days until the earliest critical cookie expires
      - live_check (bool | None): True if Instagram accepted the session
      - message (str): human-readable summary
    """
    path = _cookies_path()
    report: dict = {
        "ok": False,
        "missing_file": False,
        "missing_cookies": [],
        "expired_cookies": [],
        "days_until_expiry": None,
        "live_check": None,
        "message": "",
    }

    # --- File existence ---
    if not path.exists():
        report["missing_file"] = True
        report["message"] = f"Cookie file not found: {path}"
        return report

    # --- Parse cookies ---
    try:
        jar = MozillaCookieJar(str(path))
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        report["message"] = f"Failed to parse cookie file: {e}"
        return report

    ig_cookies = {c.name: c for c in jar if ".instagram.com" in (c.domain or "")}

    # --- Check critical cookies exist ---
    for name in _KEY_COOKIES:
        if name not in ig_cookies:
            report["missing_cookies"].append(name)

    if report["missing_cookies"]:
        report["message"] = (
            f"Missing critical cookies: {', '.join(report['missing_cookies'])}"
        )
        return report

    # --- Check expiry ---
    now = datetime.now(timezone.utc).timestamp()
    earliest_expiry_days = None

    for name in _KEY_COOKIES:
        cookie = ig_cookies[name]
        if cookie.expires and cookie.expires > 0:
            remaining = (cookie.expires - now) / 86400  # convert to days
            if remaining <= 0:
                report["expired_cookies"].append(name)
            elif earliest_expiry_days is None or remaining < earliest_expiry_days:
                earliest_expiry_days = remaining

    report["days_until_expiry"] = (
        int(earliest_expiry_days) if earliest_expiry_days is not None else None
    )

    if report["expired_cookies"]:
        report["message"] = (
            f"Expired cookies: {', '.join(report['expired_cookies'])}. "
            "Please re-export your Instagram cookies."
        )
        return report

    # --- Live check: hit Instagram with cookies and see if we're logged in ---
    try:
        cookies_dict = {c.name: c.value for c in jar if ".instagram.com" in (c.domain or "")}
        resp = curl_requests.get(
            "https://www.instagram.com/accounts/edit/",
            impersonate="chrome",
            cookies=cookies_dict,
            timeout=15,
            allow_redirects=False,
        )
        # If logged in → 200; if not → 302 redirect to login
        if resp.status_code == 200:
            report["live_check"] = True
        else:
            report["live_check"] = False
            report["message"] = (
                f"Instagram session appears invalid (HTTP {resp.status_code}). "
                "Cookies may be revoked — please re-export."
            )
            return report
    except Exception as e:
        logger.warning("Live cookie check failed (network issue?): %s", e)
        report["live_check"] = None  # inconclusive

    # --- All good ---
    report["ok"] = True
    days_msg = (
        f"{report['days_until_expiry']} days until expiry"
        if report["days_until_expiry"] is not None
        else "no expiry set"
    )
    report["message"] = f"Cookies healthy ({days_msg})"

    # Warn if expiring soon
    if report["days_until_expiry"] is not None and report["days_until_expiry"] <= 7:
        report["ok"] = False  # treat as unhealthy
        report["message"] = (
            f"⚠️ Cookies expiring in {report['days_until_expiry']} days! "
            "Please re-export your Instagram cookies soon."
        )

    return report


def send_cookie_alert(report: dict) -> None:
    """Email admins when cookie health is bad."""
    from django.core.mail import EmailMessage

    if report["ok"]:
        return  # no alert needed

    subject = "⚠️ TRIGGER ENGINE: Instagram Cookie Alert"
    body = f"""\
Instagram cookie health check failed.

Status: {report['message']}

Details:
  - Missing file: {report['missing_file']}
  - Missing cookies: {report['missing_cookies'] or 'none'}
  - Expired cookies: {report['expired_cookies'] or 'none'}
  - Days until expiry: {report['days_until_expiry'] or 'unknown'}
  - Live check passed: {report['live_check']}

Action required:
  1. Open Instagram in your browser (logged in)
  2. Export cookies using a browser extension (Netscape/txt format)
  3. Upload the file to: {_cookies_path()}
"""

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=EMAIL_HOST_USER,
            to=ADMIN_EMAILS,
        )
        email.send(fail_silently=False)
        logger.info("Cookie alert email sent to admins")
    except Exception:
        logger.exception("Failed to send cookie alert email")
