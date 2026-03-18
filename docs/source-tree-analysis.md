# Reqruit — Source Tree Analysis

> Annotated directory structure with purpose descriptions for each critical folder.

**Generated**: 2026-03-14 | **Scan Level**: Deep

---

## Project Root

```
reqruit/
├── src/                          # Application source (Python package)
│   ├── __init__.py               # Package init, version metadata
│   ├── api/                      # Layer 7: FastAPI routes, middleware, DI
│   │   ├── main.py               # ★ App factory (create_app), lifespan, exception handlers
│   │   ├── dependencies.py       # Dependency injection registry (14 repo providers + auth)
│   │   ├── middleware/
│   │   │   └── logging.py        # Request logging (request_id, user_id, duration_ms)
│   │   └── routes/
│   │       ├── auth.py           # POST register/login/refresh, GET /me
│   │       ├── profile.py        # Profile CRUD + resume upload/parse
│   │       ├── jobs.py           # Job CRUD + contacts + cascade delete
│   │       ├── apply.py          # Cover letter generation (SSE + HITL review)
│   │       ├── track.py          # Kanban board + application status machine
│   │       ├── interviews.py     # Interview CRUD + questions + mock sessions
│   │       └── outreach.py       # Outreach message generation + send tracking
│   │
│   ├── core/                     # Cross-cutting concerns
│   │   ├── config.py             # Pydantic Settings (10 sub-models, @lru_cache)
│   │   ├── exceptions.py         # AppError hierarchy (11 exception types)
│   │   ├── security.py           # JWT create/decode + bcrypt hash/verify
│   │   └── logging.py            # structlog config (dev=console, prod=JSON)
│   │
│   ├── db/                       # Layer 1: Database connections + schemas
│   │   ├── mongodb.py            # Beanie 2.0 init (AsyncMongoClient, 14 models)
│   │   ├── weaviate_client.py    # Weaviate v4 async client (4 collections, HNSW)
│   │   ├── base_document.py      # TimestampedDocument (created_at, updated_at hooks)
│   │   └── documents/            # Beanie Document models
│   │       ├── user.py           # User (email, hashed_password, is_active)
│   │       ├── profile.py        # Profile (skills, target_roles, preferences)
│   │       ├── resume.py         # Resume (raw_text, parsed_data, parse_status)
│   │       ├── job.py            # Job (title, company, requirements, salary)
│   │       ├── company.py        # Company (name, domain, tech_stack, research)
│   │       ├── contact.py        # Contact (name, role, linkedin_url)
│   │       ├── application.py    # Application (user↔job link, status machine)
│   │       ├── document.py       # DocumentRecord (cover letters, tailored resumes)
│   │       ├── outreach.py       # OutreachMessage (content, is_sent, sent_at)
│   │       ├── interview.py      # Interview (type, questions, prep notes)
│   │       ├── star_story.py     # STARStory (situation/task/action/result)
│   │       ├── llm_usage.py      # LLMUsage (tokens, cost, latency tracking)
│   │       ├── mock_session.py   # MockInterviewSession (Q&A feedback, scores)
│   │       ├── refresh_token.py  # RefreshToken (jti, family_id, rotation)
│   │       ├── enums.py          # 6 enums (ApplicationStatus, DocumentType, etc.)
│   │       └── embedded.py       # Shared sub-models (SalaryRange, etc.)
│   │
│   ├── repositories/             # Layer 2: Data access (Repository Pattern)
│   │   ├── base.py               # BaseRepository[T] generic CRUD (10 methods)
│   │   ├── weaviate_base.py      # WeaviateRepository (vector ops, multi-tenancy)
│   │   ├── user_repository.py
│   │   ├── profile_repository.py
│   │   ├── resume_repository.py
│   │   ├── job_repository.py
│   │   ├── company_repository.py
│   │   ├── contact_repository.py
│   │   ├── application_repository.py
│   │   ├── document_repository.py    # Versioned creation with retry
│   │   ├── outreach_repository.py
│   │   ├── interview_repository.py
│   │   ├── star_story_repository.py
│   │   ├── llm_usage_repository.py
│   │   ├── mock_session_repository.py
│   │   ├── refresh_token_repository.py  # Family-level revocation
│   │   ├── resume_chunk_repository.py   # Weaviate: resume chunks
│   │   ├── cover_letter_repository.py   # Weaviate: cover letter embeddings
│   │   └── star_story_embedding_repository.py  # Weaviate: STAR stories
│   │
│   ├── services/                 # Layer 6: Business logic orchestration
│   │   ├── indexing_service.py   # RAG write path (fetch→chunk→embed→store)
│   │   └── metrics_service.py    # LLM usage aggregation & budget checks
│   │
│   ├── llm/                      # Layer 4: LLM Provider abstraction
│   │   ├── models.py             # TaskType enum, routing table, cost table
│   │   ├── manager.py            # ModelManager (task→model routing, singleton)
│   │   ├── circuit_breaker.py    # Per-provider circuit breaker (3 failures → open)
│   │   ├── cost_tracker.py       # Async callback: token counting → MongoDB
│   │   └── providers/            # Provider-specific configs
│   │
│   ├── agents/                   # Layer 5: Specialized AI agents
│   │   ├── base.py               # BaseAgent abstract class (LangGraph callable)
│   │   ├── cover_letter.py       # RequirementsAnalyst + CoverLetterWriter
│   │   ├── interview_prep.py     # BehavioralQuestionGenerator + MockInterviewer + Summarizer
│   │   └── outreach.py           # OutreachComposer
│   │
│   ├── workflows/                # Layer 5: LangGraph state machines
│   │   ├── states/
│   │   │   └── cover_letter.py   # CoverLetterState TypedDict
│   │   ├── graphs/
│   │   │   └── cover_letter.py   # Graph: analyze→memories→write→review (HITL)
│   │   └── checkpointer.py       # MongoDBSaver for workflow persistence
│   │
│   ├── rag/                      # Layer 3: Retrieval-Augmented Generation
│   │   ├── embeddings.py         # BGE-small-en-v1.5 (init/close/embed, async)
│   │   ├── retriever.py          # Weaviate search bridge (hybrid + semantic)
│   │   └── chunker.py            # Document-aware + fixed-size chunking
│   │
│   ├── memory/                   # Layer 3: Agent memory system
│   │   ├── types.py              # MemoryItem, MemoryContext dataclasses
│   │   ├── recipes.py            # Per-agent retrieval config table
│   │   ├── retrieval.py          # Memory retrieval orchestrator
│   │   └── summarizer.py         # LLM-powered message compression
│   │
│   └── guardrails/               # Input/output safety
│       ├── pii_detector.py       # Regex: email, phone, SSN, credit card, IPv4
│       ├── input_validator.py    # Pydantic→rules→OpenAI Moderation (layered)
│       └── output_validator.py   # Schema→rules→Groq self-check (layered)
│
├── tests/                        # Test suite (768 passing)
│   ├── conftest.py               # Root fixtures: test_settings, async client
│   ├── unit/
│   │   ├── conftest.py           # Mock Beanie document settings (no DB needed)
│   │   ├── test_health.py
│   │   ├── test_documents.py
│   │   ├── test_base_repository.py
│   │   ├── test_llm/             # 5 files (routing, circuit breaker, cost, etc.)
│   │   ├── test_agents/          # 6 files (base, cover letter, interview, outreach)
│   │   ├── test_memory/          # 3 files (recipes, retrieval, summarizer)
│   │   ├── test_rag/             # 4 files (embeddings, retriever, chunker)
│   │   ├── test_services/        # 1 file (indexing service)
│   │   ├── test_api/             # 13 files (all route modules + cascade delete)
│   │   ├── test_auth/            # 2 files (security, auth routes)
│   │   ├── test_guardrails/      # 3 files (PII, input, output)
│   │   ├── test_evaluation/      # 2 files (logging, metrics)
│   │   ├── test_deployment/      # 1 file (health checks)
│   │   ├── test_repositories/    # 8 files (all concrete repos)
│   │   └── test_workflows/       # 2 files (checkpointer, cover letter graph)
│   └── integration/              # Real LLM/DB calls (manual runs)
│
├── docker/
│   ├── Dockerfile                # Multi-stage build (builder + runtime)
│   ├── docker-compose.yml        # app + mongodb:7 + weaviate:1.28.4
│   └── docker-compose.dev.yml    # Dev overrides (hot-reload, debug logging)
│
├── docs/                         # Documentation (this folder)
│   ├── ARCHITECTURE.md           # System design deep-dive (original)
│   ├── API_REFERENCE.md          # Endpoint reference (original)
│   ├── DATA_MODEL.md             # Schema reference (original)
│   ├── DEVELOPMENT_GUIDE.md      # Setup guide (original)
│   ├── PROJECT_SUMMARY.md        # Design decisions (original)
│   └── DETAILED_PLAN.md          # Implementation plan (original)
│
├── migrations/                   # (empty — MongoDB is schema-less)
├── pyproject.toml                # Dependencies, build config, pytest config
├── ruff.toml                     # Linting rules (E,W,F,I,N,UP,B,SIM,ASYNC)
├── uv.lock                      # Dependency lock file
├── deploy.sh                     # Bash deploy script (git pull + docker compose)
├── CLAUDE.md                     # AI assistant context file
├── LICENSE
└── README.md                     # Project overview with lifecycle diagram
```

---

## Critical Folders Summary

| Folder | Purpose | Key Entry Points |
|--------|---------|-----------------|
| `src/api/` | HTTP layer — routes, middleware, DI | `main.py:create_app()` |
| `src/core/` | Cross-cutting — config, auth, exceptions, logging | `config.py:get_settings()` |
| `src/db/` | Database connections + document schemas | `mongodb.py:connect_mongodb()` |
| `src/repositories/` | Data access layer (never query DB directly) | `base.py:BaseRepository[T]` |
| `src/services/` | Business logic orchestration | `indexing_service.py:IndexingService` |
| `src/llm/` | LLM provider abstraction + routing | `manager.py:ModelManager` |
| `src/agents/` | Specialized AI agents (6 total) | `base.py:BaseAgent` |
| `src/workflows/` | LangGraph state machine definitions | `graphs/cover_letter.py` |
| `src/rag/` | Embedding, chunking, retrieval | `embeddings.py:init_embeddings()` |
| `src/memory/` | Per-agent memory retrieval recipes | `retrieval.py:retrieve_memories()` |
| `src/guardrails/` | Input/output validation + PII detection | `input_validator.py:validate_text()` |
| `tests/unit/` | 768 fast unit tests (no external deps) | `conftest.py` |
| `docker/` | Container definitions | `docker-compose.yml` |
