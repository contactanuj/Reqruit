# Reqruit — Deployment Guide

> Docker, deploy script, and infrastructure reference.

**Generated**: 2026-03-14 | **Scan Level**: Deep

---

## Infrastructure Components

| Service | Image | Port | Volume | Purpose |
|---------|-------|------|--------|---------|
| app | Custom (Dockerfile) | 8000 | src/:ro | FastAPI application |
| mongodb | mongo:7 | 27017 | mongodb_data | Operational database (14 collections) |
| weaviate | semitechnologies/weaviate:1.28.4 | 8080, 50051 | weaviate_data | Vector database (4 collections) |

---

## Docker Architecture

### Multi-Stage Dockerfile

```dockerfile
# Stage 1: Builder
FROM python:3.13-slim-bookworm
# Install uv, copy pyproject.toml + uv.lock, run uv sync --no-dev --frozen

# Stage 2: Runtime
FROM python:3.13-slim-bookworm
# Copy .venv from builder, copy src/
# Health check: GET /health/ready every 30s
# CMD: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### docker-compose.yml Services

**app**:
- Build context: project root
- Env: loads `.env` file
- Depends on: mongodb, weaviate (service_started)
- Volumes: `src/` mounted read-only (prod safety)
- Restart: unless-stopped

**mongodb**:
- No auth configured (dev); production should use MONGO_INITDB_ROOT_USERNAME/PASSWORD
- Persistent volume: `mongodb_data`
- Restart: unless-stopped

**weaviate**:
- `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: true` (dev)
- `DEFAULT_VECTORIZER_MODULE: none` (app-side embeddings)
- Production: use `AUTHENTICATION_APIKEY_ENABLED: true`
- Persistent volume: `weaviate_data`
- Ports: 8080 (REST), 50051 (gRPC for v4 client batch ops)

### Dev Overrides (docker-compose.dev.yml)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

- Adds `--reload` (hot-reload on source changes)
- Adds `--log-level debug`
- Mounts `src/` read-write (for reload tracking)
- Single worker (--reload incompatible with --workers > 1)

---

## Deploy Script (`deploy.sh`)

Simple bash deploy script with safety features:

```bash
./deploy.sh              # Standard deploy (git pull + docker compose up)
./deploy.sh --build      # Force image rebuild
./deploy.sh --down-volumes  # DANGER: Wipe data and redeploy (requires confirmation)
```

### Flow

1. `git pull --ff-only` (fast-forward only, fails on divergence)
2. Verify `.env` exists
3. Optional: `docker compose down -v` (requires typing "yes")
4. Stop app container (keep DB/Weaviate running)
5. `docker compose up -d` (with --build if requested)
6. Wait for readiness (polls `/health/ready` every 5s, up to 60s)
7. Show `docker compose ps` on success

### Design

- **Idempotent**: Safe to re-run
- **DB-aware**: Keeps infrastructure running during app updates
- **Simple**: No Kubernetes, Helm, or CI runners (local-first)

---

## Health Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness | `{"status": "healthy", "app": "reqruit", "version": "0.1.0", "environment": "..."}` |
| `GET /health/ready` | Readiness | `{"status": "ready", "mongodb": {"status": "ok"}, "weaviate": {"status": "ok"}}` |

Docker health check uses `/health/ready` with: interval 30s, start_period 60s, retries 3.

---

## Production Checklist

1. **JWT_SECRET_KEY**: Set to a strong random value (>=32 bytes)
2. **MongoDB auth**: Enable MONGO_INITDB_ROOT_USERNAME/PASSWORD
3. **Weaviate auth**: Set AUTHENTICATION_APIKEY_ENABLED=true + AUTHENTICATION_APIKEY_ALLOWED_KEYS
4. **CORS origins**: Restrict from permissive dev settings
5. **LLM API keys**: Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY
6. **LangSmith**: Set LANGCHAIN_TRACING_V2=true for production tracing
7. **Rate limits**: Adjust RATE_LIMIT_MAX_LLM_REQUESTS_PER_HOUR
8. **Logging**: APP_ENV=production enables JSON log output
9. **SSL/TLS**: Configure reverse proxy (nginx/caddy) in front of uvicorn

---

## Local Development Setup

```bash
# Infrastructure only (develop outside Docker)
docker compose -f docker/docker-compose.yml up -d mongodb weaviate

# Run app locally with hot-reload
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Verify everything is connected
curl http://localhost:8000/health/ready
# → {"status":"ready","mongodb":{"status":"ok"},"weaviate":{"status":"ok"}}
```
