"""Application configuration for the core app."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Register signals when the core app is ready."""

    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "core"

    def ready(self):
        """Register application components."""
        pass
