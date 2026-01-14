from django.db import models


class ReelInsight(models.Model):
    source_url = models.URLField()

    original_language = models.CharField(max_length=5)

    transcript_original = models.TextField()  # Hindi (Devanagari) / Marathi / English
    transcript_english = models.TextField()  # Always English

    triggers = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.source_url
