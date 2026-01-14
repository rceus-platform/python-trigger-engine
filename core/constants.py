import json
import os

secrets = {}

if os.getenv("DEBUG") == "True":
    try:
        with open("secrets.dev.json") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        print("Warning: secrets.dev.json not found. Using environment variables.")
else:
    if "APP_SECRET_JSON" in os.environ:
        with open(os.environ["APP_SECRET_JSON"]) as f:
            secrets = json.load(f)
    else:
        print("Warning: APP_SECRET_JSON not set. Using environment variables.")

GEMINI_API_KEY = secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
EMAIL_HOST_PASSWORD = secrets.get("EMAIL_HOST_PASSWORD") or os.environ.get(
    "EMAIL_HOST_PASSWORD"
)
GDRIVE_FOLDER_ID = secrets.get("GDRIVE_FOLDER_ID") or os.environ.get("GDRIVE_FOLDER_ID")

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = "587"
EMAIL_USE_TLS = "True"
EMAIL_HOST_USER = "inout440@gmail.com"
DAILY_RECALL_EMAIL = "21rhi21@gmail.com"
