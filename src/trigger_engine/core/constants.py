"""Central configuration constants for the Trigger Engine."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# Helpers & Secrets Resolution
# ============================================================

# Load local .env if present (lives at repo root — 4 levels up from core/)
_dotenv_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)

# Load production VM secrets JSON if present
SECRET_PATH = Path("/opt/secrets/python-trigger-engine.json")
_secrets: dict[str, str] = {}
if SECRET_PATH.exists():
    try:
        with open(SECRET_PATH, encoding="utf-8") as f:
            _secrets = json.load(f)
    except Exception:
        pass


def _get_secret(key: str, default: str | None = None) -> str | None:
    """Fetch configuration from environment variables, secrets JSON, or fallback default."""
    val = os.getenv(key)
    if val is not None and val != "":
        return val
    sec_val = _secrets.get(key)
    if sec_val is not None and sec_val != "":
        return str(sec_val)
    return default


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Safely parse boolean environment variables."""
    val = _get_secret(key)
    if val is None:
        return default
    return str(val).lower() in {"1", "true", "yes", "on"}


# ============================================================
# API Keys & Secrets
# ============================================================

_raw_keys = [
    _get_secret("GEMINI_API_KEY_1"),
    _get_secret("GEMINI_API_KEY_2"),
    _get_secret("GEMINI_API_KEY"),
]
GEMINI_API_KEYS: list[str] = [k for k in _raw_keys if k]
GEMINI_API_KEY: str | None = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None

EMAIL_HOST_PASSWORD = _get_secret("EMAIL_HOST_PASSWORD")
GDRIVE_FOLDER_ID = _get_secret("GDRIVE_FOLDER_ID")
SITE_PASSCODE = _get_secret("SITE_PASSCODE", "1234")

# ============================================================
# Runtime Flags & Paths
# ============================================================

DEBUG = _get_env_bool("DEBUG", default=False)
INSTAGRAM_COOKIES_PATH = _get_secret("INSTAGRAM_COOKIES_PATH", "/opt/cookies/instagram.txt")

# ============================================================
# Email Configuration
# ============================================================

EMAIL_HOST = _get_secret("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(_get_secret("EMAIL_PORT", "587") or "587")
EMAIL_USE_TLS = _get_env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = _get_secret("EMAIL_HOST_USER", "inout440@gmail.com")

_daily_emails = _get_secret(
    "DAILY_RECALL_EMAILS",
    "21rhi21@gmail.com,rhishichikhalkar21@gmail.com",
) or ""
DAILY_RECALL_EMAILS: list[str] = [e.strip() for e in _daily_emails.split(",") if e.strip()]

_admin_emails = _get_secret(
    "ADMIN_EMAILS",
    "21rhi21@gmail.com,rhishichikhalkar21@gmail.com",
) or ""
ADMIN_EMAILS: list[str] = [e.strip() for e in _admin_emails.split(",") if e.strip()]
