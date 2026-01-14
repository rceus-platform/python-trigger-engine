import time
from pathlib import Path

from django.core.management.base import BaseCommand

MEDIA_DIR = Path("media")


class Command(BaseCommand):
    help = "Delete leftover media files older than 1 hour"

    def handle(self, *args, **options):
        if not MEDIA_DIR.exists():
            return

        now = time.time()

        for f in MEDIA_DIR.iterdir():
            if f.is_file():
                age = now - f.stat().st_mtime
                if age > 3600:  # 1 hour
                    f.unlink()
                    self.stdout.write(f"Deleted {f.name}")
