# Contributing to Python Trigger Engine

Thank you for your interest in contributing to **python-trigger-engine**! This document explains the development workflow and coding standards for this project.

---

## Development Setup

### Prerequisites

- **Python**: 3.12+
- **Package Manager**: [uv](https://docs.astral.sh/uv/)
- **Media Engine**: `ffmpeg` installed on your system PATH (`brew install ffmpeg` on macOS)

### Setup Instructions

```bash
# 1. Clone the repository
git clone git@github.com:rceus-platform/python-trigger-engine.git
cd python-trigger-engine

# 2. Install dependencies & pre-commit hooks
make install

# 3. Create local environment configuration
cp .env.example .env
# Edit .env to populate local environment variables
```

---

## Development Workflow

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Write tests first** — this project follows Test-Driven Development (TDD):
   - Place core tests under `tests/core/`
   - Use `pytest` fixtures from `tests/conftest.py`

3. **Run tests & quality checks** before committing:
   ```bash
   make test     # Runs pytest suite with coverage
   make lint     # Runs ruff linter & formatter check
   make format   # Automatically fixes formatting issues
   ```

4. **Commit with clear messages** following [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add audio deduplication via MD5 hash
   fix: resolve cookie path handling in reel downloader
   docs: update infrastructure provisioning guide
   ```

5. **Open a Pull Request** against `main`:
   - Ensure all GitHub Actions workflows (`CI`) pass cleanly.
   - Include a concise summary of the changes and testing evidence.

---

## Code Standards

- **Formatting & Linting**: Managed by `ruff` (configured in `pyproject.toml` and enforced via `pre-commit`).
- **Imports**: Clean absolute imports (`from trigger_engine.core.services import ...`).
- **Architecture**: Keep business logic in `src/trigger_engine/core/services/` decoupled from HTTP views.
- **Environment Variables**: Never hardcode API keys or secret tokens. Access configuration through `trigger_engine.core.constants`.

---

## Project Structure Conventions

| Path | Purpose |
|------|---------|
| `src/trigger_engine/settings/` | Django settings (`base.py`, `local.py`, `production.py`) |
| `src/trigger_engine/core/` | Django app containing models, views, and business services |
| `src/trigger_engine/core/services/` | Core services (Gemini AI, audio extraction, reel downloading) |
| `tests/` | Pytest suite mirroring `src/trigger_engine/` |
| `infra/` | Production VM provisioning scripts & Systemd configurations |
