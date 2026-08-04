"""Production settings — inherits from base with security hardening."""

import os

from .base import *  # noqa: F403

DEBUG = False

# Production Secret Key (loads from environment variable or constants)
SECRET_KEY = os.getenv("SECRET_KEY") or getattr(constants, "SECRET_KEY", SECRET_KEY)

# Production Allowed Hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "trigger-engine.rceus.duckdns.org,localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]

# Security Hardening
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Browser Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
