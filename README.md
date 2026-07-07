# Trigger Engine

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Django](https://img.shields.io/badge/Django-6.0+-092E20.svg)](https://www.djangoproject.com/)
[![uv](https://img.shields.io/badge/uv-fast-ff0000.svg)](https://github.com/astral-sh/uv)

## Overview

The **Trigger Engine** is a robust backend automation and integration service built with **Django** and **Python 3.12**. It acts as a central hub for processing media, handling automated workflows, and generating AI-driven insights. 

Key capabilities include interacting with Instagram via `instaloader`, downloading media using `yt-dlp`, performing speech-to-text with `deepgram-sdk`, and utilizing Google's Generative AI (`google-genai`).

## Key Features

- **Media Processing & Extraction**: Integrated with `yt-dlp` and `instaloader` to fetch media content from various social platforms.
- **AI & Transcriptions**: Uses `google-genai` for generative AI tasks and `deepgram-sdk` for high-speed audio transcription.
- **Automated Workflows**: Configurable task scheduling (e.g., daily recall emails).
- **Advanced Scraping**: Bypasses restrictions using `curl-cffi` and extracts data via `parsel`.

## Tech Stack

- **Framework**: [Django 6.0+](https://www.djangoproject.com/)
- **Runtime**: [Python 3.12+](https://www.python.org/)
- **AI / ML**: `google-genai`, `deepgram-sdk`
- **Media / Scraping**: `yt-dlp`, `instaloader`, `curl-cffi`, `parsel`
- **Server**: `gunicorn`, `uvicorn`

## System Requirements

### FFmpeg Requirement

This project requires **FFmpeg** to be installed on the system for media processing.

**Windows**:
Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add `ffmpeg/bin` to your system `PATH`.

**Ubuntu / Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

## Getting Started

### Prerequisites

- **Python**: 3.12 or higher
- **uv**: Astral's high-speed Python package manager (`pip install uv`)

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository_url>
   cd python-trigger-engine/application-source
   ```

2. **Sync dependencies:**
   ```bash
   uv sync
   ```

### Configuration

Create a `.env` file in the `application-source` directory (do not commit this file).

```env
# Django Settings
SECRET_KEY=your_django_secret_key
DEBUG=True

# API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
GOOGLE_API_KEY=your_google_genai_key
```

### Running the Service

Start the development server:
```bash
cd application-source
uv run python manage.py runserver
```

## Production Deployment & Scheduling

### Recall Email Scheduling

To schedule daily recall emails (9am, 12pm, 3pm, 6pm, 9pm) in a production environment (e.g., Oracle VM):

1. Deploy the code to `/opt/apps/python-trigger-engine/`.
2. Install the crontab:
   ```bash
   crontab /opt/apps/python-trigger-engine/application-source/crontab.txt
   ```
3. Verify the installation:
   ```bash
   crontab -l
   ```

*Application logs are written to `application-source/logs/cron.log`.*

## License

This project is licensed under MIT License.
