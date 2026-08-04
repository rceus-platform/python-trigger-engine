"""Django models for storing reel insights."""

from django.db import models


class ReelInsight(models.Model):
    """Persistent metadata for a processed Instagram reel."""

    source_url = models.URLField()
    original_language = models.CharField(max_length=10)
    transcript_original = models.TextField()
    transcript_english = models.TextField()
    triggers = models.TextField()
    title = models.CharField(max_length=200, null=True, blank=True)
    source_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True, db_index=True
    )

    audio_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )

    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.source_url)
