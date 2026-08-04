# Trigger Engine Infrastructure

This directory contains infrastructure automation, provisioning scripts, and environment configurations for deploying **python-trigger-engine** to production.

## Deployment Target

- **Infrastructure**: Linux VM (Oracle Cloud Infrastructure / Ubuntu VPS)
- **Application Directory**: `/opt/apps/python-trigger-engine`
- **Process Manager**: Systemd (`python-trigger-engine.service`)
- **Reverse Proxy**: Nginx with Certbot SSL (`trigger-engine.rceus.duckdns.org`)
- **Python Runtime**: Python 3.12 managed via `uv`

---

## Directory Structure

```
infra/
├── README.md                # Infrastructure documentation (this file)
├── cron/
│   └── crontab.conf         # Production cron schedule (recall emails)
└── provisioning/
    ├── manifest.json        # Application runtime configuration
    ├── provision.sh         # Server setup, Systemd & Nginx provisioning script
    └── system-packages.json # OS-level system dependencies (apt packages)
```

---

## Provisioning Component Breakdown

### 1. `provisioning/manifest.json`
Defines runtime settings used by `provision.sh` to configure Gunicorn/Uvicorn, Systemd unit files, and Nginx reverse proxy routes:

- **runtime**: `python`
- **working_dir**: `.`
- **start_command**: `.venv/bin/gunicorn trigger_engine.asgi:application -k uvicorn.workers.UvicornWorker ...`
- **domain**: `trigger-engine.rceus.duckdns.org`
- **port**: `8000`

### 2. `provisioning/system-packages.json`
Specifies required Ubuntu OS `apt` packages installed automatically during server provisioning:

- **Core**: `jq`, `curl`, `ca-certificates`, `nginx`, `build-essential`, `clang`, `openssl`, `ffmpeg`
- **Browser Automation**: `chromium-browser`, `chromium-chromedriver`, `xvfb`
- **Python**: `python3-pip`, `python3-venv`, `python3-dev`

### 3. `provisioning/provision.sh`
Idempotent bash script executed on the VM by GitHub Actions (`cd.yml` and `provision.yml`). Responsibilities:

1. Installs missing OS packages listed in `system-packages.json`.
2. Syncs Python virtual environment via `uv sync`.
3. Runs database migrations (`manage.py migrate`).
4. Collects static files (`manage.py collectstatic`).
5. Generates and registers Systemd service `/etc/systemd/system/${APP_NAME}.service`.
6. Configures Nginx reverse proxy and reloads Systemd services.

---

## Scheduled Jobs (Cron)

Cron configuration is stored in `infra/cron/crontab.conf`. To apply the production schedule on the VM:

```bash
crontab /opt/apps/python-trigger-engine/infra/cron/crontab.conf
```

Verify active cron jobs:
```bash
crontab -l
```

---

## GitHub Actions Integration

- **`cd.yml`**: Automatically calls `infra/provisioning/provision.sh` via SSH on code push to `main`.
- **`provision.yml`**: Can be triggered manually via `workflow_dispatch` to perform initial server bootstrapping.
