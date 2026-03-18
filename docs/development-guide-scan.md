# Reqruit — Development Guide (Deep Scan)

> Setup, commands, conventions, and testing reference.

**Generated**: 2026-03-14 | **Scan Level**: Deep

---

## Prerequisites

- **Python**: 3.11+ (runtime uses 3.13, `.python-version` for pyenv)
- **uv**: Rust-based Python package manager ([install](https://docs.astral.sh/uv/))
- **Docker Desktop**: For MongoDB and Weaviate containers
- **Git**: Version control

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd Reqruit
cd backend && uv sync      # Install all dependencies (including dev)

# 2. Start infrastructure (from repo root)
docker compose -f docker/docker-compose.yml up -d mongodb weaviate

# 3. Configure environment
cp backend/.env.example backend/.env  # Edit with your API keys

# 4. Run API server (from backend/)
uv run uvicorn src.api.main:app --reload

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| APP_NAME | No | reqruit | Application name |
| APP_ENV | No | development | Environment (development/production) |
| DEBUG | No | true | Debug mode |
| MONGODB_URL | No | mongodb://localhost:27017 | MongoDB connection string |
| MONGODB_DATABASE | No | job_hunt | Database name |
| WEAVIATE_URL | No | http://localhost:8080 | Weaviate REST URL |
| WEAVIATE_API_KEY | No | "" | Weaviate auth (prod only) |
| JWT_SECRET_KEY | **Yes (prod)** | change-me-in-production | Token signing secret |
| JWT_ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 15 | Access token TTL |
| REFRESH_TOKEN_EXPIRE_DAYS | No | 7 | Refresh token TTL |
| ANTHROPIC_API_KEY | No | "" | Claude API key (primary LLM) |
| OPENAI_API_KEY | No | "" | OpenAI key (data extraction + moderation) |
| GROQ_API_KEY | No | "" | Groq key (free fallback LLM) |
| LANGCHAIN_TRACING_V2 | No | false | Enable LangSmith tracing |
| LANGCHAIN_API_KEY | No | "" | LangSmith API key |
| LANGCHAIN_PROJECT | No | reqruit | LangSmith project name |
| RATE_LIMIT_MAX_LLM_REQUESTS_PER_HOUR | No | 10 | Per-user LLM budget |

---

## Commands

### Development

```bash
uv sync                                                    # Install/update deps
uv run uvicorn src.api.main:app --reload                   # Dev server with hot-reload
docker compose -f docker/docker-compose.yml up -d mongodb weaviate  # Start infra only
```

### Testing

```bash
# Standard (Linux/Mac)
uv run pytest tests/unit/ -q              # Run unit tests
uv run pytest tests/unit/ --cov           # With coverage
uv run pytest tests/unit/ -k "test_auth"  # Filter by name

# Windows workaround (uv run pytest trampoline fails)
.venv/Scripts/python.exe -m pytest tests/unit/ -q
```

**Test config** (`pyproject.toml`):
- `asyncio_mode = "auto"` — No `@pytest.mark.asyncio` needed
- `testpaths = ["tests"]`
- Deprecation warnings suppressed

### Linting

```bash
uv run ruff check src/ tests/              # Lint
uv run ruff check --fix src/ tests/        # Lint + auto-fix
uv run ruff format src/ tests/             # Format
```

**Ruff config** (`ruff.toml`): target py311, line-length 88, rules: E,W,F,I,N,UP,B,SIM,ASYNC. Ignores: E501 (line length), B008 (Depends in defaults).

### Docker

```bash
# Full stack with hot-reload
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

# Production
docker compose -f docker/docker-compose.yml up -d

# Stop and wipe data
docker compose -f docker/docker-compose.yml down -v
```

---

## Conventions

| Convention | Details |
|-----------|---------|
| **Async everywhere** | All I/O uses async/await |
| **Repository Pattern** | Never query DB from routes/services; always via repository |
| **Pydantic models** | Shared across API schemas, DB documents, validation |
| **App factory** | `create_app()` for testability (no module-level app) |
| **structlog** | Structured JSON logging in production, colored console in dev |
| **Owner scoping** | All queries filter by user_id (data isolation) |
| **No API versioning** | Single frontend, learning project |
| **Exception hierarchy** | `AppError` base → HTTP status code mapping |

---

## Testing Architecture

### Structure

```
tests/
├── conftest.py           # test_settings, async client (patches all DB/LLM connections)
├── unit/
│   ├── conftest.py       # _mock_beanie_document_settings (no MongoDB needed)
│   ├── test_health.py    # 2 tests
│   ├── test_documents.py # 66 tests (Beanie schemas, defaults, validation)
│   ├── test_llm/         # 77 tests (routing, circuit breaker, cost tracking)
│   ├── test_agents/      # 41 tests (base agent, all concrete agents)
│   ├── test_memory/      # 74 tests (recipes, retrieval, summarizer)
│   ├── test_rag/         # 67 tests (embeddings, retriever, chunker)
│   ├── test_api/         # 34+ tests (all route modules, cascade delete)
│   ├── test_auth/        # JWT + auth routes
│   ├── test_guardrails/  # 67 tests (PII, input, output validation)
│   ├── test_evaluation/  # 30 tests (logging, metrics)
│   ├── test_deployment/  # ~16 tests (health checks)
│   ├── test_repositories/ # All concrete repos
│   └── test_workflows/   # Checkpointer, cover letter graph
└── integration/          # Real LLM/DB calls (manual only)
```

### Key Fixtures

- **`test_settings`**: In-memory settings with test database (`job_hunt_test`)
- **`client`**: httpx AsyncClient with ASGI transport (no real server), all external deps mocked
- **`_mock_beanie_document_settings`**: Autouse, patches all 14 Document models to work without init_beanie()

### Test Count: 768 passing (0 failures, 7 xfailed)

---

## Adding New Features

### New API Endpoint

1. Add route function in `src/api/routes/<module>.py`
2. Add repository if new collection needed (`src/repositories/`)
3. Add Beanie Document model if needed (`src/db/documents/`)
4. Register Document in `src/db/mongodb.py:_get_document_models()`
5. Add dependency provider in `src/api/dependencies.py`
6. Write tests in `tests/unit/test_api/`

### New Agent

1. Create agent class extending `BaseAgent` in `src/agents/`
2. Define `TaskType` mapping in `src/llm/models.py:ROUTING_TABLE`
3. Add memory recipe in `src/memory/recipes.py` if context needed
4. Wire into workflow graph or call directly from route handler
5. Write tests in `tests/unit/test_agents/`

### New Workflow

1. Define state TypedDict in `src/workflows/states/`
2. Build graph in `src/workflows/graphs/` using StateGraph
3. Add init/close functions following cover letter pattern
4. Register in lifespan (startup/shutdown) in `src/api/main.py`
5. Write tests in `tests/unit/test_workflows/`
