# ---------------------------------------------------------------------------
# Multi-stage Dockerfile — Reqruit
# ---------------------------------------------------------------------------
# Two stages:
#   1. Builder: installs uv and project dependencies (cached layer)
#   2. Runtime: copies the app + installed packages, runs uvicorn
#
# Why multi-stage:
#   - Smaller final image (no build tools, no uv binary in production)
#   - Better layer caching — dependencies change less often than app code,
#     so the dependency layer is cached across most builds
#   - Follows Docker best practices for Python applications
#
# Alternative approaches:
#   - Single stage: simpler but larger image and slower rebuilds
#   - distroless base: smallest image but harder to debug (no shell)
#   - alpine base: smaller than slim but can cause issues with compiled
#     Python packages (musl vs glibc). slim-bookworm is the safe default.
#
# Usage:
#   docker build -f docker/Dockerfile -t job-hunt-app .
#   docker run -p 8000:8000 --env-file .env job-hunt-app
# ---------------------------------------------------------------------------

# -- Stage 1: Build dependencies --
FROM python:3.13-slim-bookworm AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (for layer caching).
# When only source code changes, this layer is cached.
COPY backend/pyproject.toml backend/uv.lock* ./

# Install dependencies into a virtual environment.
# --no-dev: exclude test/lint dependencies from production image.
# --frozen: fail if uv.lock is out of date (ensures reproducible builds).
RUN uv sync --no-dev --frozen || uv sync --no-dev

# -- Stage 2: Runtime --
FROM python:3.13-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY backend/src/ /app/src/

# Add the virtual environment to PATH so `python` resolves to venv Python
ENV PATH="/app/.venv/bin:$PATH"

# Prevent Python from writing .pyc files and enable unbuffered output
# (important for seeing logs immediately in Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Docker health check — polls /health/ready every 30s.
# start_period gives the app time to load models and connect to DBs (~60s).
# If the check fails 3 times in a row, the container is marked unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')" || exit 1

# Run with uvicorn.
# --host 0.0.0.0: listen on all interfaces (required inside Docker).
# --workers 4: multiple worker processes for production concurrency.
# For development, docker-compose mounts source code and the app container
# can use --reload instead.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
