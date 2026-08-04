"""Local development settings — inherits everything from base."""

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["*"]
