# Reqruit

> AI-powered job hunting assistant — a production-grade deep-dive into agentic AI engineering.

Reqruit automates the full job search lifecycle: resume parsing, semantic job matching, AI cover letter generation with human-in-the-loop review, interview preparation, and pipeline tracking. Built as a learning vehicle for 12 agentic AI concepts implemented at production standards.

```text
494 unit tests passing  |  0 lint errors  |  Python 3.11+  |  FastAPI + LangGraph + MongoDB + Weaviate
```

---

## What It Does

```text
 ┌─────────────────────────────────────────────────────────────────────┐
 │                     JOB HUNT LIFECYCLE                              │
 ├──────────────┬──────────────┬──────────────┬──────────────┬─────────┤
 │  1. PROFILE  │  2. DISCOVER │   3. APPLY   │  4. PREPARE  │ 5.TRACK │
 │              │              │              │              │         │
 │ Upload       │ Search jobs  │ Tailor       │ Company      │ Kanban  │
 │ resume       │ Match to     │ resume per   │ deep-dive    │ board   │
 │              │ profile      │ JD           │              │         │
 │ Extract      │              │ Generate     │ Behavioral   │ Status  │
 │ skills &     │ Research     │ cover letter │ questions    │ machine │
 │ experience   │ companies    │ (HITL SSE)   │ from JD      │         │
 │              │              │              │              │         │
 │ Build        │ Find         │ Draft        │ STAR story   │ Notes & │
 │ profile      │ contacts     │ outreach     │ preparation  │ follow- │
 │              │              │              │              │ ups     │
 └──────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

Every critical action — sending a cover letter, submitting an application, sending outreach — has a **human approval gate** before execution.

---

## Architecture

```text
                         ┌─────────────────────────┐
                         │     FastAPI (async)      │
                         │  JWT auth  │  SSE stream │
                         └─────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
   ┌─────▼──────┐            ┌────────▼───────┐          ┌────────▼───────┐
   │  Services  │            │  Agent Layer   │          │   Workflows    │
   │            │            │  (13 agents)   │          │  (LangGraph)   │
   │ Indexing   │            │                │          │                │
   │ Metrics    │            │ ResumeParser   │          │ CoverLetter    │
   │            │            │ CoverLetter    │          │ (HITL + SSE)   │
   └─────┬──────┘            │ JobMatcher(n/i)│          └────────┬───────┘
         │                   └────────┬───────┘                   │
         │                            │                            │
         │              ┌─────────────▼────────────────────────────┤
         │              │           LLM Provider Layer              │
         │              │                                           │
         │              │  Task-based routing → Claude / GPT / Groq │
         │              │  Circuit breaker  │  Cost tracking        │
         │              └─────────────┬─────────────────────────────┘
         │                            │
         └───────────────┬────────────┘
                         │
         ┌───────────────┼───────────────────────────────┐
         │               │                               │
   ┌─────▼──────┐  ┌─────▼──────────┐          ┌────────▼───────┐
   │  MongoDB   │  │   Weaviate v4  │          │   RAG System   │
   │  (Beanie)  │  │  (4 vector     │          │                │
   │            │  │   collections) │          │ BGE-small      │
   │ 12 collec- │  │                │          │ embeddings     │
   │ tions      │  │ Hybrid search  │          │ (384d, free)   │
   │ Checkpoints│  │ BM25 + vector  │          │ Doc-aware      │
   │ LLM usage  │  │ HNSW index     │          │ chunking       │
   └────────────┘  └────────────────┘          └────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11+ | `StrEnum`, `match`, full async |
| Package Manager | uv | 10-100x faster than pip/Poetry |
| API | FastAPI (full async) | Pydantic-native, auto OpenAPI, SSE |
| Operational DB | MongoDB + Beanie 2.0 ODM | Schema-flexible, Pydantic documents |
| Vector DB | Weaviate v4 (Docker) | HNSW, hybrid BM25+vector, multi-tenancy |
| Agent Framework | LangGraph | State machines, HITL, persistent checkpoints |
| LLM Primary | Anthropic Claude (Sonnet) | Best reasoning and creative writing |
| LLM Secondary | OpenAI GPT-4o-mini | Structured JSON extraction |
| LLM Free Fallback | Groq Llama 3.3 70B | 500K tokens/day free |
| Embeddings | BAAI/bge-small-en-v1.5 | Free, local, 384d, zero API cost |
| Observability | LangSmith + structlog | Dev tracing + prod JSON logs |
| Auth | PyJWT (HS256) | Access (15min) + Refresh (7d) tokens |
| Streaming | Server-Sent Events (SSE) | Real-time LangGraph output |
| Testing | pytest + pytest-asyncio | 494 unit tests, `asyncio_mode=auto` |
| Linting | ruff | Replaces black + isort + flake8 |
| Containers | Docker Compose | App + MongoDB + Weaviate |
| CI | GitHub Actions | Auto-test on every push |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker + Docker Compose

### 1. Install

```bash
git clone https://github.com/your-username/reqruit.git
cd reqruit
cd backend && uv sync
```

### 2. Configure

```bash
cp backend/.env.example backend/.env
# Minimum required: set GROQ_API_KEY (free at console.groq.com)
# Optional: ANTHROPIC_API_KEY, OPENAI_API_KEY for higher-quality outputs
# Required: change JWT_SECRET_KEY from default in production
```

### 3. Start Infrastructure

```bash
docker compose -f docker/docker-compose.yml up -d mongodb weaviate
# MongoDB: localhost:27017
# Weaviate: localhost:8080
```

### 4. Run the API

```bash
cd backend
uv run uvicorn src.api.main:app --reload
# API:    http://localhost:8000
# Docs:   http://localhost:8000/docs  (Swagger UI, dev only)
# Health: http://localhost:8000/health
```

### 5. Register and Use

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# Login → get access_token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

---

## API Overview

| Route Group | Prefix | Stage | Key Endpoints |
|-------------|--------|-------|---------------|
| Auth | `/auth` | — | register, login, refresh, me |
| Profile | `/profile` | 1 – Setup | GET/PATCH profile, upload resume |
| Jobs | `/jobs` | 2 – Discover | manual add, list, delete, contacts |
| Apply | `/apply` | 3 – Apply | cover letter (SSE + HITL) |
| Track | `/track` | 5 – Track | kanban board, status transitions |
| System | — | — | `/health`, `/health/ready` |

See [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) for the complete endpoint reference with schemas and error codes.

---

## Key Patterns

### Human-in-the-Loop with SSE

```text
POST /apply/applications/{id}/cover-letter  → 202 + thread_id (no LLM calls)
GET  /apply/applications/{id}/cover-letter/stream?thread_id=X
     → SSE stream: node_complete events → awaiting_review (graph pauses)
POST /apply/applications/{id}/cover-letter/review
     → {"action": "approve"} or {"action": "revise", "feedback": "..."}
     → graph resumes from checkpoint, no re-computation
```

### Application State Machine

```text
SAVED ──→ APPLIED ──→ INTERVIEWING ──→ OFFERED ──→ ACCEPTED (terminal)
    │                              └──→ REJECTED  (terminal)
    └──────────────────────────────────→ WITHDRAWN (terminal)
```

### Two-Query Pattern (No N+1)

```python
# One query for applications, one batch query for all jobs
applications = await app_repo.get_for_user(user_id)
job_ids = [app.job_id for app in applications]
jobs = await job_repo.find_by_ids(job_ids)       # IN query, not per-app
job_map = {str(j.id): j for j in jobs}
```

### LLM Routing with Fallback

```text
Task: COVER_LETTER
  → Try Claude Sonnet    (available + circuit closed) → use it
  → Try GPT-4o           (not configured)             → skip
  → Try Groq Llama 70B  (fallback)                   → use if Claude fails
```

---

## Implementation Status

| Module | Status | Tests |
|--------|--------|-------|
| 1. Foundation | ✅ Complete | 2 |
| 2. Database Layer | ✅ Complete | 66 |
| 3. LLM Provider | ✅ Complete | 77 |
| 4. Agent Architecture | ✅ Complete | 41 |
| 5. Memory Systems | ✅ Complete | 74 |
| 6. RAG Pipeline | ✅ Complete | 67 |
| 7. API Layer | ✅ Complete | 34 |
| 8. Guardrails | ✅ Complete | 67 |
| 9. Evaluation | ✅ Complete | 30 |
| 10. Deployment | ✅ Complete | 36 |
| **Total** | **10/10 complete** | **494** |

---

## Agentic AI Concepts Covered

| # | Concept | Where |
|---|---------|-------|
| 1 | LangGraph state machines | `backend/src/workflows/graphs/` |
| 2 | Human-in-the-loop (HITL) | `apply.py` + `cover_letter.py` graph |
| 3 | Persistent checkpoints | `backend/src/workflows/checkpointer.py` (MongoDBSaver) |
| 4 | SSE streaming | `GET /apply/.../cover-letter/stream` |
| 5 | Multi-provider LLM routing | `backend/src/llm/manager.py` + `models.py` |
| 6 | Circuit breaker | `backend/src/llm/circuit_breaker.py` |
| 7 | Cost tracking | `backend/src/llm/cost_tracker.py` → `llm_usage` collection |
| 8 | RAG with hybrid search | `backend/src/rag/` + Weaviate hybrid (BM25 + vector) |
| 9 | Document-aware chunking | `backend/src/rag/chunker.py` |
| 10 | Per-agent memory recipes | `backend/src/memory/recipes.py` |
| 11 | Input/output guardrails | `backend/src/guardrails/` |
| 12 | PII detection | `backend/src/guardrails/pii_detector.py` |

---

## Testing

All test commands run from the `backend/` directory:

```bash
cd backend

# Unit tests (fast, no external deps)
.venv/Scripts/python.exe -m pytest tests/unit/ -q     # Windows
uv run pytest tests/unit/ -q                           # Mac/Linux

# With coverage
uv run pytest --cov=src tests/unit/

# Single module
uv run pytest tests/unit/test_llm/ -v
```

Test conventions: see [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md).

---

## Documentation

| Document | Contents |
|----------|---------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, component breakdown, data flows, key patterns |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | All endpoints with schemas, error codes, examples |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | MongoDB collections, Weaviate schema, indexes, enums |
| [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md) | Setup, conventions, adding features, debugging |
| [`CLAUDE.md`](CLAUDE.md) | AI assistant context (project rules for Claude Code) |

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full template.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Recommended | — | Free LLM fallback (Llama 3.3 70B) |
| `ANTHROPIC_API_KEY` | Optional | — | Primary LLM (Claude Sonnet) |
| `OPENAI_API_KEY` | Optional | — | Secondary LLM + Moderation API |
| `MONGODB_URL` | Yes | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | No | `job_hunt` | Database name |
| `WEAVIATE_URL` | Yes | `http://localhost:8080` | Weaviate instance URL |
| `JWT_SECRET_KEY` | Yes | `change-me-in-production` | **Change this** |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token TTL |
| `LANGCHAIN_TRACING_V2` | Optional | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | Optional | — | LangSmith API key |
| `APP_ENV` | No | `development` | `development` or `production` |
| `DEBUG` | No | `true` | Enables Swagger UI, verbose logs |

---

## License

Educational and personal use.
