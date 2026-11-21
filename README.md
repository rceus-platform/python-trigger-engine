# Trigger Engine

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Django](https://img.shields.io/badge/Django-6.0+-092E20.svg)](https://www.djangoproject.com/)
[![uv](https://img.shields.io/badge/uv-fast-ff0000.svg)](https://github.com/astral-sh/uv)

## Overview

The **Trigger Engine** is a robust backend automation and integration service built with **Django** and **Python 3.12**. It acts as a central hub for processing media, handling automated workflows, and generating AI-driven insights. 

Key capabilities include interacting with Instagram via `instaloader`, downloading media using `yt-dlp`, and performing AI audio transcription with Google Generative AI (`google-genai`).

## Key Features

- **Media Processing & Extraction**: Integrated with `yt-dlp` and `instaloader` to fetch media content from various social platforms.
- **AI & Transcriptions**: Uses `google-genai` for multi-key rotated AI audio transcription and content synthesis.
- **Automated Workflows**: Configurable task scheduling (e.g., daily recall emails).
- **Advanced Scraping**: Bypasses restrictions using `curl-cffi` and extracts data via `parsel`.

## Tech Stack

- **Framework**: [Django 6.0+](https://www.djangoproject.com/)
- **Runtime**: [Python 3.12+](https://www.python.org/)
- **AI / ML**: `google-genai`
- **Media / Scraping**: `yt-dlp`, `instaloader`, `curl-cffi`, `parsel`
- **Server**: `gunicorn`, `uvicorn`

## System Requirements

### FFmpeg Requirement

This project requires **FFmpeg** to be installed on the system for media processing.

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu / Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

## Getting Started

### Prerequisites

- **Python**: 3.12 or higher
- **uv**: Astral's high-speed Python package manager (`pip install uv` or `brew install uv`)

### Quickstart

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd python-trigger-engine
   ```

2. **Install dependencies and setup pre-commit:**
   ```bash
   make install
   # or: uv sync && uv run pre-commit install
   ```

3. **Configure Environment:**
   Copy `.env.example` to `.env` in the root directory:
   ```bash
   cp .env.example .env
   ```

4. **Run Database Migrations:**
   ```bash
   make migrate
   # or: uv run python src/trigger_engine/manage.py migrate
   ```

5. **Start Development Server:**
   ```bash
   make run
   # or: uv run python src/trigger_engine/manage.py runserver 0.0.0.0:8000
   ```

## Development Commands

| Command | Description |
|---|---|
| `make install` | Install dependencies and pre-commit hooks |
| `make run` | Start Django dev server |
| `make migrate` | Apply database migrations |
| `make makemigrations` | Create database migrations |
| `make test` | Run pytest suite |
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff |
| `make clean` | Clean build artifacts and cache |

## Project Structure

```
python-trigger-engine/
├── .dockerignore
├── .editorconfig
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yaml
├── infra/
│   ├── README.md
│   ├── cron/
│   │   └── crontab.conf
│   └── provisioning/
│       ├── manifest.json
│       ├── provision.sh
│       └── system-packages.json
├── Makefile
├── pyproject.toml
├── README.md
├── src/
│   └── trigger_engine/
│       ├── manage.py
│       ├── asgi.py
│       ├── wsgi.py
│       ├── urls.py
│       ├── settings/
│       │   ├── base.py
│       │   ├── local.py
│       │   └── production.py
│       └── core/
└── tests/
```

## CI/CD & GitHub Workflows

The repository includes standard GitHub Actions workflows under `.github/workflows/`:

- **`ci.yml`**: Runs `ruff` linting, `pytest` test suite, and builds the Docker image on PRs and pushes to `main`.
- **`cd.yml`**: Continuous Deployment pipeline that automatically updates the VM application via SSH when changes are merged to `main`.
- **`provision.yml`**: Manual workflow for provisioning and bootstrapping the application server and system services on the production VM.
- **`db-backup.yml`**: Scheduled daily automated backup of the SQLite database to GitHub Artifacts.
- **`release.yml`**: Automatically builds python packages and creates GitHub Releases when version tags (`v*`) are pushed.

## Production Deployment & Scheduling

### Recall Email Scheduling

To schedule daily recall emails in production:

1. Deploy the code to `/opt/apps/python-trigger-engine/`.
2. Install the crontab:
   ```bash
   crontab /opt/apps/python-trigger-engine/infra/cron/crontab.conf
   ```
3. Verify the installation:
   ```bash
   crontab -l
   ```

## License

This project is licensed under MIT License.

