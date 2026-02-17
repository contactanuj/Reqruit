# Reqruit

> AI-powered job hunting assistant built with production-grade agentic AI patterns.

Reqruit automates the entire job search lifecycle — from resume parsing and job discovery to cover letter generation and interview preparation. Built as a hands-on deep-dive into 12+ agentic AI concepts using LangGraph, MongoDB, Weaviate, and multi-provider LLM routing.

---

## What It Does

```text
PROFILE SETUP ──> DISCOVER JOBS ──> APPLY ──> PREPARE ──> TRACK
```

| Stage | What Happens | Agents |
|-------|-------------|--------|
| **Profile Setup** | Upload resume, extract skills and experience, build career profile | ResumeParser, EntityExtractor, ProfileEnhancer |
| **Discover Jobs** | Search listings, match against profile, research companies, find contacts | JobSearcher, JobMatcher, CompanyResearcher, POCFinder |
| **Apply** | Tailor resumes per JD, generate cover letters, draft outreach messages | ResumeTailor, CoverLetterWriter, OutreachComposer |
| **Prepare** | Company deep-dives, behavioral questions, STAR stories, mock interviews | CompanyBrief, QuestionGenerator, STARHelper, MockInterviewer |
| **Track** | Pipeline dashboard, follow-up reminders, response analytics | UI + background jobs |

Every critical action (sending a cover letter, submitting an application) goes through a human approval gate before execution.

---

## Architecture

```text
                            FastAPI (async)
                                 |
            +--------------------+--------------------+
            |                    |                    |
       Service Layer        Agent Layer         Workflow Engine
      (orchestration)    (13 specialized)      (LangGraph graphs)
            |                    |                    |
            +--------------------+--------------------+
                                 |
                       LLM Provider Layer
                  (routing, circuit breaker, cost tracking)
                                 |
                  +--------------+--------------+
                  |                             |
             MongoDB (Beanie)           Weaviate v4
          12 operational collections   4 vector collections
          + workflow checkpoints       hybrid search (BM25 + vector)
```

### Key Design Choices

- **13 specialized agents** instead of one mega-agent — each focused, testable, cost-optimized with its own LLM model
- **Task-based LLM routing** — cover letters go to Claude Sonnet, data extraction to GPT-4o-mini, quick tasks to Groq (free)
- **Per-agent memory recipes** — each agent has tuned relevance/recency retrieval weights, not one-size-fits-all
- **Document-aware RAG chunking** — resumes and JDs split by section headings, keeping semantic context intact
- **Delete-before-reindex** — idempotent re-indexing that handles structural changes correctly
- **Circuit breaker** per LLM provider — skips known-broken providers, auto-recovers when they return

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11+ | Industry standard for AI/ML |
| Package Manager | uv | 10-100x faster than Poetry |
| API | FastAPI (full async) | Pydantic-native, auto OpenAPI docs |
| Operational DB | MongoDB (Beanie 2.0) | Flexible documents, async Pydantic ODM |
| Vector DB | Weaviate v4 | Dedicated HNSW, free hybrid search |
| Agent Framework | LangGraph | State machines, checkpoints, HITL |
| LLM Primary | Anthropic Claude | Best reasoning and creative writing |
| LLM Secondary | OpenAI GPT | Strong at structured JSON extraction |
| LLM Free Fallback | Groq Llama | 500K tokens/day free tier |
| Embeddings | BAAI/bge-small-en-v1.5 | Free, local, 384 dims, zero API cost |
| Observability | LangSmith + structlog | Dev tracing + production metrics |
| Auth | JWT via PyJWT | Stateless access (15min) + refresh (7d) tokens |
| Streaming | SSE | Real-time agent output, token-by-token |
| Testing | pytest + pytest-asyncio | 327+ unit tests, async-native |
| Linting | ruff | Replaces black + isort + flake8, 10-100x faster |
| Containers | Docker Compose | Same config for dev and prod |
| CI | GitHub Actions | Auto-test on every push |

---

## Project Structure

```text
src/
├── api/               # FastAPI routes, middleware, dependencies
│   ├── main.py        # App factory, health check, exception handlers
│   ├── dependencies.py
│   ├── middleware/
│   └── routes/
├── core/              # Config, security, exceptions
│   ├── config.py      # Pydantic Settings with composed sub-models
│   └── exceptions.py  # AppError hierarchy (maps to HTTP status codes)
├── db/
│   ├── mongodb.py     # Beanie init + async connection lifecycle
│   ├── weaviate_client.py
│   └── documents/     # 12 Beanie document models (Pydantic-based)
├── repositories/      # Data access layer (Repository Pattern)
│   ├── base.py        # BaseRepository[T] — generic CRUD for MongoDB
│   ├── weaviate_base.py  # WeaviateRepository — generic vector ops
│   └── *_repository.py   # Collection-specific repos
├── services/          # Business logic orchestration
│   └── indexing_service.py  # RAG write-path (fetch → chunk → embed → store)
├── llm/
│   ├── manager.py     # ModelManager with task-based routing
│   ├── providers/     # Provider configs (Anthropic, OpenAI, Groq)
│   ├── circuit_breaker.py
│   └── cost_tracker.py
├── agents/            # 13 specialized AI agents
│   ├── base.py        # BaseAgent — callable as LangGraph nodes
│   └── cover_letter.py
├── workflows/
│   ├── states/        # LangGraph TypedDict state definitions
│   ├── graphs/        # Workflow graph definitions with HITL
│   └── checkpointer.py
├── rag/
│   ├── embeddings.py  # BGE-small-en-v1.5 lifecycle (init/close/get)
│   ├── retriever.py   # Weaviate search bridge (embed + search)
│   └── chunker.py     # Document-aware + fixed-size chunking
├── memory/
│   ├── types.py       # MemoryItem, MemoryContext dataclasses
│   ├── recipes.py     # Per-agent retrieval recipe config table
│   ├── retrieval.py   # Memory retrieval orchestrator
│   └── summarizer.py  # LLM-powered message summarization
└── guardrails/
    ├── input_validator.py
    ├── output_validator.py
    └── pii_detector.py
tests/
├── unit/              # 327+ tests, no external deps, runs in CI
├── integration/       # Real LLM/DB calls, manual runs
└── conftest.py
docker/
├── docker-compose.yml # App + MongoDB + Weaviate
└── Dockerfile
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker and Docker Compose (for MongoDB + Weaviate)

### Setup

```bash
# Clone and install
git clone https://github.com/your-username/reqruit.git
cd reqruit
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys (at minimum, set GROQ_API_KEY — it's free)

# Start infrastructure
docker compose -f docker/docker-compose.yml up -d mongodb weaviate

# Run the API server
uv run uvicorn src.api.main:app --reload
```

### Running Tests

```bash
uv run pytest                        # All tests
uv run pytest tests/unit/ -v         # Unit tests (verbose)
uv run pytest --cov                  # With coverage report
```

### Linting

```bash
uv run ruff check src/ tests/        # Check for issues
uv run ruff check --fix src/ tests/  # Auto-fix
uv run ruff format src/ tests/       # Format code
```

---

## Data Model

### MongoDB (12 Collections)

| Collection | Purpose |
|------------|---------|
| `users` | Authentication (email, hashed_password) |
| `profiles` | Career data (skills, preferences, target roles) |
| `resumes` | Resume documents (raw text, parsed data, versions) |
| `jobs` | Job listings (title, description, requirements, salary) |
| `companies` | Company info (culture, tech stack, research notes) |
| `contacts` | LinkedIn POCs per company |
| `applications` | Pipeline tracking (status, match score, timestamps) |
| `documents` | AI-generated content (cover letters, tailored resumes) |
| `outreach_messages` | LinkedIn messages (recruiter, engineer, manager templates) |
| `interviews` | Interview records (schedule, type, notes, questions) |
| `star_stories` | Behavioral examples (situation, task, action, result) |
| `llm_usage` | Cost tracking (agent, model, tokens, cost per request) |

### Weaviate (4 Vector Collections)

| Collection | Purpose | Embedding |
|------------|---------|-----------|
| `ResumeChunk` | Resume sections for semantic matching | BGE-small (384d) |
| `JobEmbedding` | Job descriptions for similarity search | BGE-small (384d) |
| `CoverLetterEmbedding` | Past cover letters for reuse | BGE-small (384d) |
| `STARStoryEmbedding` | Behavioral stories matched to questions | BGE-small (384d) |

---

## Implementation Progress

| Module | Status | Tests |
|--------|--------|-------|
| 1. Foundation | Complete | 2 |
| 2. Database Layer | Complete | 66 |
| 3. LLM Provider | Complete | 77 |
| 4. Agent Architecture | Complete | 41 |
| 5. Memory Systems | Complete | 74 |
| 6. RAG Pipeline | Complete | 67 |
| 7. API Layer | Planned | -- |
| 8. Guardrails | Planned | -- |
| 9. Evaluation | Planned | -- |
| 10. Deployment | Planned | -- |

**Total: 327 tests passing across 6 completed modules.**

---

## Agentic AI Concepts Covered

This project is a learning vehicle for production-grade agentic AI patterns:

| # | Concept | Implementation |
|---|---------|---------------|
| 1 | LangGraph | Workflow orchestration with state machines and cycles |
| 2 | LangSmith | Observability, tracing, evaluation datasets |
| 3 | Database Design | MongoDB documents + Weaviate vectors |
| 4 | Context Management | Conversation state, workflow checkpoints |
| 5 | Short-term Memory | LangGraph messages with sliding window + summarization |
| 6 | Long-term Memory | MongoDB collections + Weaviate embeddings |
| 7 | Evaluation | Quality metrics, golden datasets, layered testing |
| 8 | Guardrails | Input/output validation, PII detection, LLM moderation |
| 9 | Chain of Thought | Structured reasoning in specialized agents |
| 10 | Model Selection | Task-based routing with circuit breaker and cost budgets |
| 11 | RAG | Document-aware chunking, hybrid search, per-agent retrieval |
| 12 | Human-in-the-Loop | Approval gates before critical actions |

---

## Environment Variables

See [`.env.example`](.env.example) for the full template. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Recommended | Free LLM fallback (500K tokens/day) |
| `ANTHROPIC_API_KEY` | Optional | Primary LLM (Claude Sonnet) |
| `OPENAI_API_KEY` | Optional | Secondary LLM (GPT-4o-mini) |
| `MONGODB_URL` | Yes | Default: `mongodb://localhost:27017` |
| `WEAVIATE_URL` | Yes | Default: `http://localhost:8080` |
| `JWT_SECRET_KEY` | Yes | Change from default in production |
| `LANGCHAIN_API_KEY` | Optional | LangSmith tracing (5K traces/month free) |

---

## Documentation

- [`docs/DETAILED_PLAN.md`](docs/DETAILED_PLAN.md) — Complete implementation plan with technical specs for all 10 modules
- [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md) — Comprehensive design discussion history and decision rationale
- [`CLAUDE.md`](CLAUDE.md) — Project context for AI-assisted development sessions

---

## License

This project is for educational and personal use.
