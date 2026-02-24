"""Central configuration constants for the Trigger Engine."""

import json
import os

from dotenv import load_dotenv

# ============================================================
# Helpers
# ============================================================


def _get_env_bool(name: str, default: bool = False) -> bool:
    """
    Safely read boolean env vars.
    Accepts: 1, true, yes, on (case-insensitive)
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


# ============================================================
# Secrets loading (VM / Local)
# ============================================================

SECRET_PATH = "/opt/secrets/python-trigger-engine.json"

if os.path.exists(SECRET_PATH):
    # --- Production (VM) secrets ---
    with open(SECRET_PATH, encoding="utf-8") as f:
        _secrets = json.load(f)

    GEMINI_API_KEYS = [
        _secrets.get("GEMINI_API_KEY_1"),
        _secrets.get("GEMINI_API_KEY_2"),
    ]
    EMAIL_HOST_PASSWORD = _secrets.get("EMAIL_HOST_PASSWORD")
    GDRIVE_FOLDER_ID = _secrets.get("GDRIVE_FOLDER_ID")
    DEEPGRAM_API_KEY = _secrets.get("DEEPGRAM_API_KEY")

else:
    # --- Local development (.env) ---
    load_dotenv()

    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

    GEMINI_API_KEYS = [
        os.getenv("GEMINI_API_KEY_1"),
        os.getenv("GEMINI_API_KEY_2"),
    ]


GEMINI_API_KEY = next((key for key in GEMINI_API_KEYS if key), None)


# ============================================================
# Runtime flags
# ============================================================

DEBUG = _get_env_bool("DEBUG", default=False)


# ============================================================
# External tools / paths
# ============================================================

INSTAGRAM_COOKIES_PATH = "/opt/cookies/instagram.txt"


# ============================================================
# Email configuration
# ============================================================

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = "587"
EMAIL_USE_TLS = "True"
EMAIL_HOST_USER = "inout440@gmail.com"

DAILY_RECALL_EMAILS = [
    "21rhi21@gmail.com",
    "rhishichikhalkar21@gmail.com",
]
