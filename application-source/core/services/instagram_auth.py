"""Centralized Instagram authentication and session management."""

import logging
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import instaloader

from core.constants import INSTAGRAM_COOKIES_PATH

logger = logging.getLogger(__name__)


def load_cookies_into_session(session, cookies_path: Path) -> bool:
    """Load Netscape-format cookies into a requests-like session."""
    if not cookies_path.exists():
        logger.warning(
            "Instagram cookies file NOT found at %s. Proceeding anonymously.",
            cookies_path,
        )
        return False

    try:
        logger.info("Loading Instagram cookies from %s", cookies_path)
        cookie_jar = MozillaCookieJar(str(cookies_path))
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        logger.info("Successfully loaded cookies into session")
        return True
    except Exception:
        logger.exception("Failed to load Instagram cookies from %s", cookies_path)
        return False


def get_instaloader(**instaloader_kwargs) -> instaloader.Instaloader:
    """Returns an Instaloader instance with cookies loaded (if available)."""
    loader = instaloader.Instaloader(**instaloader_kwargs)
    load_cookies_into_session(loader.context._session, Path(INSTAGRAM_COOKIES_PATH))
    return loader
