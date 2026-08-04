# Changelog

All notable changes to **python-trigger-engine** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-02

### Added
- Standardized Django project architecture under `src/trigger_engine/` and `tests/`.
- Multi-key rotation support for Google Gemini AI (`google-genai`) audio transcription and post synthesis.
- Media processing service integration using `yt-dlp` and `instaloader`.
- Audio extraction pipeline using `ffmpeg` with MD5 audio hashing for duplicate detection.
- Daily recall email notification service for stored Instagram reels and media.
- Multi-environment settings architecture (`settings/base.py`, `settings/local.py`, `settings/production.py`).
- Pre-commit hooks with `ruff` linting and formatting.
- `Makefile` developer tooling (`make install`, `make run`, `make test`, `make lint`).
- Multi-stage `Dockerfile` and `docker-compose.yaml` using `uv`.
- Production-grade infrastructure automation under `infra/provisioning/` (`provision.sh`, `manifest.json`, `system-packages.json`).
- Automated production-grade GitHub Actions workflows (`ci.yml`, `cd.yml`, `provision.yml`, `db-backup.yml`, `release.yml`).
