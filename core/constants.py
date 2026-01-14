import json
import os

from dotenv import load_dotenv

SECRET_PATH = "/opt/secrets/python-trigger-engine.json"

if os.path.exists(SECRET_PATH):
    with open(SECRET_PATH) as f:
        secrets = json.load(f)

    GEMINI_API_KEY = secrets.get("GEMINI_API_KEY")
    EMAIL_HOST_PASSWORD = secrets.get("EMAIL_HOST_PASSWORD")
    GDRIVE_FOLDER_ID = secrets.get("GDRIVE_FOLDER_ID")

else:
    # Fallback for local development
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = "587"
EMAIL_USE_TLS = "True"
EMAIL_HOST_USER = "inout440@gmail.com"
DAILY_RECALL_EMAIL = "21rhi21@gmail.com"
