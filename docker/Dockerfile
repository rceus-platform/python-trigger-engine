# ============================================================================
# Production Dockerfile for Trigger Engine
# ============================================================================
# Multi-stage build: builder installs deps, runtime is minimal.
# Final image runs as non-root user for security.
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy dependency files and README for layer caching
COPY pyproject.toml uv.lock* README.md* ./

# Install production dependencies only (no dev extras)
RUN uv sync --no-dev --frozen

# Copy source code
COPY src/ src/

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal image with only what's needed
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Install FFmpeg (required for media processing)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /build/.venv .venv
COPY --from=builder /build/src src

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check — uses the health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

# Run with gunicorn ASGI server for production concurrency
CMD ["gunicorn", "trigger_engine.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "600"]
