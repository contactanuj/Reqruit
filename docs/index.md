# Reqruit — Documentation Index

> AI-powered job hunting assistant — production-grade agentic AI learning project.

**Generated**: 2026-03-14 | **Scan Level**: Deep | **768 tests passing**

---

## Project Overview

- **Type**: Monolith Backend API
- **Language**: Python 3.11+ (runtime 3.13)
- **Architecture**: 7-layer async backend (FastAPI + LangGraph + MongoDB + Weaviate)
- **Architecture Pattern**: Layered with Repository Pattern, workflow-first agents

### Quick Reference

| Attribute | Value |
|-----------|-------|
| **Tech Stack** | FastAPI, MongoDB (Beanie 2.0), Weaviate v4, LangGraph, Claude/GPT/Groq |
| **Entry Point** | `src/api/main.py:create_app()` |
| **API Endpoints** | 53 REST endpoints + SSE streaming |
| **MongoDB Collections** | 14 |
| **Weaviate Collections** | 4 (384-dim BGE embeddings, HNSW cosine) |
| **AI Agents** | 6 specialized agents across 3 domains |
| **LLM Providers** | Anthropic (primary), OpenAI (extraction), Groq (free fallback) |
| **Auth** | JWT HS256 — access (15min) + refresh (7d) with rotation |
| **Tests** | 768 unit tests (0 failures) |

---

## Generated Documentation (Deep Scan)

- [Project Overview](./project-overview.md) — Executive summary, tech stack, module status
- [Architecture (Deep Scan)](./architecture-scan.md) — System layers, agents, workflows, data flows
- [Source Tree Analysis](./source-tree-analysis.md) — Annotated directory structure
- [API Contracts](./api-contracts.md) — All 53 endpoints with schemas and status codes
- [Data Models (Deep Scan)](./data-models-scan.md) — MongoDB + Weaviate schemas, enums, indexes
- [Development Guide (Deep Scan)](./development-guide-scan.md) — Setup, commands, conventions, testing
- [Deployment Guide](./deployment-guide.md) — Docker, deploy script, production checklist

---

## Existing Documentation (Original)

- [ARCHITECTURE.md](./ARCHITECTURE.md) — System design deep-dive (15 sections)
- [API_REFERENCE.md](./API_REFERENCE.md) — Original endpoint reference with examples
- [DATA_MODEL.md](./DATA_MODEL.md) — Original schema reference with design principles
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) — Original setup and conventions guide
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) — Design decision rationale (historical)
- [DETAILED_PLAN.md](./DETAILED_PLAN.md) — Original implementation plan (historical)

---

## Job Hunt Lifecycle

```
 1. PROFILE      2. DISCOVER     3. APPLY       4. PREPARE      5. TRACK
 ─────────────  ─────────────  ─────────────  ─────────────  ─────────────
 Upload resume  Search jobs    Tailor resume  Behavioral Qs  Kanban board
 Parse & index  Match profile  Cover letter   Mock interview  Status machine
 Build profile  Research co.   (HITL + SSE)   STAR stories   Notes & archive
                Find contacts  Draft outreach
```

---

## Getting Started

```bash
# 1. Install dependencies
uv sync

# 2. Start infrastructure
docker compose -f docker/docker-compose.yml up -d mongodb weaviate

# 3. Configure environment
cp .env.example .env  # Add API keys

# 4. Run server
uv run uvicorn src.api.main:app --reload

# 5. Verify
curl http://localhost:8000/health/ready
```

---

## AI-Assisted Development

When using AI tools to work on this codebase:

1. **Start here** — This index provides the full project map
2. **For architecture decisions** — Read [architecture-scan.md](./architecture-scan.md) or [ARCHITECTURE.md](./ARCHITECTURE.md)
3. **For API work** — Reference [api-contracts.md](./api-contracts.md) for all 53 endpoints
4. **For schema changes** — Check [data-models-scan.md](./data-models-scan.md) for all 14+4 collections
5. **For new features** — Follow patterns in [development-guide-scan.md](./development-guide-scan.md#adding-new-features)
6. **For deployment** — See [deployment-guide.md](./deployment-guide.md)

### Key Files for Context

| Purpose | File |
|---------|------|
| App factory | `src/api/main.py` |
| Config system | `src/core/config.py` |
| All exceptions | `src/core/exceptions.py` |
| Auth (JWT+bcrypt) | `src/core/security.py` |
| LLM routing | `src/llm/models.py` + `src/llm/manager.py` |
| Agent base | `src/agents/base.py` |
| Workflow graph | `src/workflows/graphs/cover_letter.py` |
| RAG indexing | `src/services/indexing_service.py` |
| Memory recipes | `src/memory/recipes.py` |
| Test fixtures | `tests/conftest.py` + `tests/unit/conftest.py` |
| AI context | `CLAUDE.md` (root) |
