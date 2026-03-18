# Reqruit — Project Overview

> AI-powered job hunting assistant built to learn production-grade agentic AI patterns.

**Generated**: 2026-03-14 | **Scan Level**: Deep | **Project Type**: Backend API (Monolith)

---

## Executive Summary

Reqruit automates the full job search lifecycle: resume parsing, semantic job matching, AI cover letter generation with human-in-the-loop review, interview preparation (behavioral questions, mock interviews, STAR stories), networking outreach, and pipeline tracking via a Kanban board.

Built as a learning vehicle for 12+ agentic AI concepts implemented at production standards: LangGraph workflows, LangSmith observability, MongoDB + Weaviate dual-database architecture, RAG with local embeddings, guardrails (input/output/PII), memory systems, human-in-the-loop approval gates, multi-provider LLM routing with circuit breakers, cost tracking, evaluation, and Docker deployment.

---

## Tech Stack Summary

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | Python | 3.11+ (runtime 3.13) | Full async everywhere |
| Package Manager | uv | Latest | Rust-based, 10-100x faster than Poetry |
| API Framework | FastAPI | >=0.115.0 | Async-native, Pydantic validation, auto OpenAPI |
| ASGI Server | Uvicorn | >=0.34.0 | With uvloop on Linux/Mac |
| Operational DB | MongoDB 7 | via Beanie 2.0 | Async PyMongo API (not Motor) |
| Vector DB | Weaviate 1.28.4 | v4 client | Collections API, HNSW + cosine |
| Agent Framework | LangGraph | >=0.4.0 | State machine workflows with checkpoints |
| Primary LLM | Claude Sonnet | via langchain-anthropic | Cover letters, interview prep, outreach |
| Secondary LLM | GPT-4o-mini | via langchain-openai | Data extraction (deterministic) |
| Free Fallback | Groq Llama 3.3 70B / 3.1 8B | via langchain-groq | 500K tokens/day free |
| Embeddings | BAAI/bge-small-en-v1.5 | 384 dims | Free, local, no API costs |
| Auth | JWT (PyJWT) | HS256 | Access (15min) + Refresh (7d) tokens |
| Observability | structlog + LangSmith | | JSON logging + trace visualization |
| Streaming | SSE (sse-starlette) | | Real-time agent output |
| Testing | pytest + pytest-asyncio | asyncio_mode=auto | 768 tests passing |
| Linting | ruff | | Replaces black + isort + flake8 |
| Containers | Docker Compose | | App + MongoDB + Weaviate |

---

## Architecture Classification

- **Repository Type**: Monolith (single cohesive codebase)
- **Architecture Pattern**: Layered (7 vertical layers)
- **API Style**: REST with SSE streaming for agent output
- **Data Strategy**: Hybrid — MongoDB for operational data (14 collections), Weaviate for vector search (4 collections)
- **Agent Pattern**: Workflow-first with LangGraph state machines

---

## Job Hunt Lifecycle (5 Stages)

```
 1. PROFILE      2. DISCOVER     3. APPLY       4. PREPARE      5. TRACK
 ─────────────  ─────────────  ─────────────  ─────────────  ─────────────
 Upload resume  Search jobs    Tailor resume  Company deep-  Kanban board
 Extract skills Match to       Generate cover dive           Status machine
 Build profile  profile        letter (HITL)  Behavioral Qs  Notes &
                Research       Draft outreach Mock interviews follow-ups
                companies      (approval gate) STAR stories
                Find contacts
```

Every critical action (sending cover letter, submitting application, sending outreach) has a **human approval gate** before execution.

---

## Module Status

| # | Module | Status | Tests |
|---|--------|--------|-------|
| 1 | Foundation | Complete | 2 |
| 2 | Database | Complete | 66 |
| 3 | LLM Provider | Complete | 77 |
| 4 | Agent Architecture | Complete | 41 |
| 5 | Memory Systems | Complete | 74 |
| 6 | RAG Pipeline | Complete | 67 |
| 7 | API Layer | Complete | 34 |
| 8 | Guardrails | Complete | 67 |
| 9 | Evaluation | Complete | 30 |
| 10 | Deployment | Complete | ~16 |
| **Total** | | **10/10 Complete** | **768 passing** |

---

## Related Documentation

- [Architecture](./architecture.md) — System design, layers, data flows
- [API Contracts](./api-contracts.md) — All 45+ endpoints with schemas
- [Data Models](./data-models.md) — MongoDB + Weaviate schemas
- [Source Tree](./source-tree-analysis.md) — Annotated directory structure
- [Development Guide](./development-guide.md) — Setup, commands, conventions
- [Deployment Guide](./deployment-guide.md) — Docker, deploy script, CI

### Existing Documentation (Original)
- [ARCHITECTURE.md](./ARCHITECTURE.md) — Original technical deep-dive
- [API_REFERENCE.md](./API_REFERENCE.md) — Original endpoint reference
- [DATA_MODEL.md](./DATA_MODEL.md) — Original schema reference
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) — Original setup guide
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) — Design decision rationale
- [DETAILED_PLAN.md](./DETAILED_PLAN.md) — Original implementation plan
