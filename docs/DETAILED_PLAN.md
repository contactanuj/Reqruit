# Reqruit - Detailed Implementation Plan

> **Purpose:** Complete implementation plan with all 10 module decisions, reasoning, and technical specifications.
> **Last Updated:** 2026-02-17

---

## Quick Reference

| # | Module | Key Decisions | Status |
|---|--------|---------------|--------|
| 1 | Foundation | uv, Hybrid structure, Pydantic Settings, Full Async | **Complete** |
| 2 | Database | MongoDB (Beanie) + Weaviate, Schema-less migrations, Repository Pattern | **Complete** |
| 3 | LLM Provider | Hybrid abstraction, Task-based routing, Circuit breaker, Real-time budgets, Groq fallback | **Complete** |
| 4 | Agent Architecture | Workflow-First, LangGraph, 13 Specialized agents, MongoDB Checkpoints, Approval gates | **Complete** |
| 5 | Memory Systems | Summarization, Hybrid storage (Mongo+Weaviate), Per-agent hybrid retrieval | **Complete** |
| 6 | RAG Pipeline | Hybrid chunking, BGE-small-en-v1.5 embeddings, Hybrid+Filtered Weaviate search | **Complete** |
| 7 | API Layer | JWT (Access+Refresh), SSE streaming + REST actions, No versioning | Planned |
| 8 | Guardrails | Layered input (Pydantic+Rules+OpenAI+LlamaGuard), Schema+Rules+Groq self-check | Planned |
| 9 | Evaluation | LangSmith + Custom logging, Layered testing (Unit+Eval+Integration) | Planned |
| 10 | Deployment | Docker Compose everywhere, Local first then Cloud, GitHub Actions CI + Manual deploy | Planned |

---

## Core Tech Stack

| Layer | Technology | Package/Library | Reason |
|-------|------------|----------------|--------|
| Language | Python 3.11+ | - | Industry standard for AI/ML |
| Package Manager | uv | `uv` | 10-100x faster than Poetry |
| API Framework | FastAPI | `fastapi`, `uvicorn` | Async-native, Pydantic integration |
| Operational DB | MongoDB | `beanie` (2.0, PyMongo async) | Flexible documents, Pydantic-native ODM |
| Vector DB | Weaviate | `weaviate-client` v4 | Dedicated HNSW, free hybrid search |
| Agent Framework | LangGraph | `langgraph` | State machines, checkpoints, HITL |
| LLM - Primary | Anthropic Claude | `langchain-anthropic` | Best reasoning, creative writing |
| LLM - Secondary | OpenAI GPT | `langchain-openai` | Good at JSON extraction |
| LLM - Free Fallback | Groq (Llama) | `langchain-groq` | 500K tokens/day free |
| Embeddings | BGE-small-en-v1.5 | `langchain-huggingface`, `sentence-transformers` | Free, local, 384 dims |
| Observability | LangSmith | `langsmith` | Auto-traces LangGraph, evaluation datasets |
| Logging | structlog | `structlog` | Structured production logging to MongoDB |
| Auth | JWT | `PyJWT[crypto]` | Stateless, FastAPI-native (python-jose unmaintained) |
| Testing | pytest | `pytest`, `pytest-asyncio`, `pytest-mock` | Async support, mocking |
| CI | GitHub Actions | - | Free 2000 min/month |
| Containers | Docker Compose | - | Same config dev + prod |

---

## Module 1: Project Foundation (Complete)

### 1.1 Package Manager: uv

- 10-100x faster installs (8s vs 180s for our stack)
- Compatible with `pyproject.toml` (no lock-in)
- Major companies adopting it

### 1.2 Project Structure: Hybrid (Layer + Domain)

- Layers for infrastructure: `api/`, `db/`, `core/`, `repositories/`, `services/`
- Domains for AI components: `agents/`, `workflows/`, `rag/`, `guardrails/`, `llm/`

### 1.3 Configuration: Pydantic Settings

- Type-safe with IDE autocomplete
- Validation at startup (fail fast)
- Shared Pydantic ecosystem with FastAPI + Beanie

### 1.4 Async Strategy: Full Async

- All I/O operations async (LLM calls, DB, vector search)
- FastAPI + Beanie + httpx + LangGraph all support async natively

---

## Module 2: Database Layer (Complete)

### 2.1 ODM: Beanie (async MongoDB ODM)

- Beanie 2.0 uses PyMongo's native async API directly (not Motor as in 1.x)
- Documents ARE Pydantic models (one definition for API + DB + validation)
- Seamless FastAPI integration

### 2.2 Architecture: MongoDB + Weaviate

**MongoDB Collections (12):**

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| users | Authentication | email, hashed_password |
| profiles | User career data | skills[], preferences{}, target_roles[] |
| resumes | Resume documents | raw_text, parsed_data{}, version, is_master |
| jobs | Job listings | title, description, requirements{}, salary{} |
| companies | Company info | name, culture_notes, tech_stack[], research{} |
| contacts | LinkedIn POCs | name, role, linkedin_url, contacted |
| applications | Pipeline items | status, match_score (db only, not exposed via API), applied_at |
| documents | Generated docs | type, content, version, is_approved |
| outreach_messages | LinkedIn messages | message_type, content, is_sent |
| interviews | Interview records | scheduled_at, type, notes{}, questions[] |
| star_stories | Behavioral examples | situation, task, action, result, tags[] |
| llm_usage | Cost tracking | agent, model, tokens, cost, timestamp |

**Weaviate Classes (4):**

| Class | Purpose | Dims | Properties |
|-------|---------|------|-----------|
| ResumeChunk | Resume sections for RAG | 384 | content, chunk_type, resume_id, user_id |
| JobEmbedding | Job description vectors | 384 | title, description_summary, job_id |
| CoverLetterEmbedding | Past cover letters | 384 | content_summary, company, role, doc_id |
| STARStoryEmbedding | Behavioral stories | 384 | story_summary, tags, story_id |

### 2.3 Migration: Schema-less + Application Defaults

- Beanie documents define defaults for new fields
- `Optional` types + default values handle missing fields
- `schema_version` field on documents for tracking
- Migration scripts for rare breaking changes

### 2.4 Document Design: Hybrid (Embedded + References)

- **Embed** small/coupled data: skills inside profiles, requirements inside jobs
- **Reference** large/independent data: applications reference jobs and users by ObjectId

### 2.5 Data Access: Repository Pattern

- Clean separation between data access and business logic
- Easy to mock for unit testing

---

## Module 3: LLM Provider Layer (Complete)

### 3.1 Abstraction: Hybrid (LangChain + Custom Wrapper)

```python
class ModelManager:
    providers = {"anthropic": ChatAnthropic, "openai": ChatOpenAI, "groq": ChatGroq, "ollama": ChatOllama}
    router = ModelRouter(config)       # Task-based routing
    cost_tracker = CostTracker()       # Real-time budgets
    circuit_breaker = CircuitBreaker() # Resilience
```

### 3.2 Routing: Task-based

| Task | Primary Model | Groq Free Fallback |
|------|--------------|-------------------|
| Resume Analysis | Claude Sonnet | No free alternative |
| Cover Letter | Claude Sonnet | Llama 3.3 70B |
| Quick Chat | Claude Haiku | Llama 3.1 8B |
| Data Extraction | GPT-4o-mini | Llama 3.3 70B |

### 3.3 Fallback: Circuit Breaker

- Track failures per provider
- After N failures, mark provider as "open" (skip it)
- After recovery time, try again ("half-open")
- Automatic recovery when service returns

### 3.4 Cost: Real-time Budgets

- Per-request logging to `llm_usage` collection
- Aggregated metrics per user/agent/model
- Spending limits prevent runaway costs

### 3.5 Free Fallback: Groq

- 500K tokens/day free, 30 RPM
- `ChatGroq` via `langchain-groq`
- No embedding support (LLM inference only)

---

## Module 4: Agent Architecture

### Approach: Workflow-First

5 stages: Profile Setup -> Discover Jobs -> Apply -> Prepare -> Track

### 4.1 Framework: LangGraph

- State machines with cycles/loops
- Built-in persistence and checkpoints
- Human-in-the-loop via `interrupt()`
- Each workflow stage = one subgraph

### 4.2 Agents: 13 Specialized Agents

| Workflow | Agents |
|----------|--------|
| Profile Setup | ResumeParser, EntityExtractor, ProfileEnhancer |
| Job Discovery | JobSearcher, JobMatcher (not yet implemented), CompanyResearcher, POCFinder |
| Application | ResumeTailor, CoverLetterWriter, OutreachComposer |
| Interview Prep | CompanyBrief, QuestionGenerator, STARHelper, MockInterviewer |

### 4.3 State: MongoDB Persistent Checkpoints

- `MongoDBSaver` from `langgraph-checkpoint-mongodb`
- 4 state layers: Conversation (messages), Workflow (checkpoints), Knowledge (collections), Semantic (Weaviate)

### 4.4 HITL: Approval Gates

- Resume tailoring -> Approve before saving
- Cover letter -> Approve before finalizing
- Outreach messages -> Approve before marking ready
- Application submission -> Confirm before status change

---

## Module 5: Memory Systems

### 5.1 Short-term Memory: Summarization

- Keep last N messages verbatim
- Summarize older messages (compress without losing key info)
- LangGraph custom message reducers

### 5.2 Long-term Memory: Hybrid (MongoDB + Weaviate)

| Data Type | Store | Why |
|-----------|-------|-----|
| User profile, preferences | MongoDB | Structured, direct lookup |
| Application history | MongoDB | Structured, recency queries |
| Past cover letters | Weaviate | Semantic similarity search |
| STAR stories | Weaviate | Match stories to questions |
| Resume chunks | Weaviate | Semantic matching to JDs |
| Company research | MongoDB | Structured, freshness-based |

### 5.3 Retrieval: Per-Agent Hybrid (Recency + Relevance)

Each agent has a tailored retrieval recipe:

| Agent | Relevance (Weaviate) | Recency (MongoDB) | Strategy |
|-------|---------------------|-------------------|----------|
| ResumeParser | 0% | 100% | Extraction only |
| ProfileEnhancer | 70% | 30% | Semantic skill matching |
| JobSearcher | 0% | 100% | Outbound search, dedup |
| JobMatcher (not yet implemented) | 60% | 40% | Semantic + calibration |
| CompanyResearcher | 0% | 100% | Freshness matters |
| POCFinder | 0% | 100% | LinkedIn lookup |
| ResumeTailor | 70% | 30% | Match experience to JD |
| CoverLetterWriter | 50% | 50% | Similar letters + style |
| OutreachComposer | 20% | 80% | Recent patterns |
| QuestionGenerator | 60% | 40% | Gap analysis + no repeats |
| STARHelper | 90% | 10% | Pure semantic matching |
| MockInterviewer | 50% | 50% | Realistic + improvement |

**Rule of thumb:**
- "Most SIMILAR?" -> Relevance (Weaviate)
- "Most RECENT?" -> Recency (MongoDB)
- "Best for THIS situation?" -> Both

---

## Module 6: RAG Pipeline

### 6.1 Chunking: Hybrid (Document-Aware + Fixed Fallback)

- **Document-aware** for known formats (resumes, JDs): each section = one chunk
- **Fixed-size fallback** (500 tokens, 50-token overlap) for unknown formats
- Resume section "Work Experience at Company X" stays together as one chunk

### 6.2 Embedding Model: BAAI/bge-small-en-v1.5

- Free, local, 384 dimensions
- `HuggingFaceEmbeddings` from `langchain-huggingface`
- Better quality than MiniLM (~40th vs ~60th on MTEB)
- Works offline after first model download
- Re-embedding at our scale: 40s to 7min (low lock-in)

**Lock-in analysis:**
- Embedding lock-in: MODERATE (re-embed needed on model change)
- LLM lock-in: NONE (LangChain abstracts all providers)
- Groq: NO embedding models (LLM inference only)

### 6.3 Search: Hybrid + Filtered (Weaviate)

- BM25 + vector combined (`hybrid` with per-agent `alpha` tuning)
- Metadata filters: `user_id`, location, role type
- All free Weaviate features

```python
# Weaviate v4 collections-based API (v3 client.query.get is deprecated)
from weaviate.classes.query import MetadataQuery, Filter

resume_chunks = client.collections.use("ResumeChunk")
response = resume_chunks.query.hybrid(
    query="Python FastAPI microservices",
    alpha=0.7,
    filters=Filter.by_property("user_id").equal(user_id),
    return_metadata=MetadataQuery(score=True),
    limit=10,
)
```

---

## Module 7: API Layer

### 7.1 Authentication: JWT (Access + Refresh Tokens)

- Access token: 15min, Refresh token: 7d with rotation
- `PyJWT[crypto]` + `passlib` (python-jose unmaintained since 2021)
- Stateless (no DB lookup per request)

**Endpoints:**
- `POST /auth/register` - Create account, return JWT pair
- `POST /auth/login` - Verify credentials, return JWT pair
- `POST /auth/refresh` - Rotate refresh token
- `GET /auth/me` - Current user from token

### 7.2 Real-time: SSE streaming + REST actions

- **SSE** for agent output streaming (token-by-token generation, progress events)
- **REST** for user actions (approve, reject, edit)
- FastAPI `StreamingResponse` + async generators
- LangGraph streaming is naturally SSE-compatible

### 7.3 Versioning: None (for now)

- Single frontend, learning project
- Can add `/api/v1/` prefix later if needed

---

## Module 8: Guardrails

### 8.1 Input Validation: Layered (Pydantic + Rules + LLM)

**Three layers:**
1. **Pydantic** - Schema validation (automatic via FastAPI)
2. **Rule-based** - PII regex, file type/size, length limits, encoding
3. **LLM moderation** - On free-text fields only

**LLM Moderation Stack (both free):**
- OpenAI Moderation API first (free, unlimited, fast)
- Llama Guard 3 via Groq second (free tier, more nuanced)

| Input Type | Pydantic | Rules | LLM |
|-----------|----------|-------|-----|
| Resume upload | File type | PDF/DOCX + max 10MB | No |
| Job URL | URL format | Domain allowlist | No |
| Free text | String type | Length + encoding | Yes |
| Profile fields | Types + ranges | Salary > 0 | No |

### 8.2 Output Validation: Schema + Rules + LLM Self-Check

- **Schema**: `with_structured_output()` from LangChain
- **Rules**: PII regex, hallucination verification against DB, tone keywords
- **Self-check**: Groq Llama 3.1 8B on critical outputs only (free, ~10-20 calls/day)

| Output | Schema | Rules | Self-Check |
|--------|--------|-------|------------|
| Cover letter | Yes | PII, tone, facts | Yes |
| Outreach message | Yes | PII, tone, length | Yes |
| Tailored resume | Yes | PII, facts | Yes |
| Parsed resume | Yes | Dates, skills | No |
| Match score | Yes | Range 0-100 | No |
| Interview questions | Yes | Role-relevant | No |
| STAR story | Yes | All 4 parts | No |

---

## Module 9: Evaluation

### 9.1 Observability: LangSmith + Custom Logging

**LangSmith (development):**
- `LANGCHAIN_TRACING_V2=true` + API key
- Auto-traces all LangGraph nodes, LLM calls, tool use
- Visual trace explorer
- Free tier: 5K traces/month

**Custom structlog (production):**
- `structlog` -> MongoDB `llm_usage` collection
- Cost aggregation per user/agent/model
- Latency percentiles, error rates, budget alerts

### 9.2 Testing: Layered (Unit + Eval + Integration)

| Layer | What | Runs | Cost |
|-------|------|------|------|
| Unit (pytest + mocks) | Logic, routing, schemas, guardrails | Every commit (CI) | Free |
| Eval datasets (LangSmith) | Agent output quality | Weekly | Free tier |
| Integration (real LLMs) | End-to-end critical paths | Manual | ~$0.50/run |

**Tools:** `pytest`, `pytest-asyncio`, `pytest-mock`, `pytest-cov`, LangSmith eval API

---

## Module 10: Deployment

### 10.1 Containerization: Docker Compose everywhere

```yaml
services:
  app:       # FastAPI application
  mongodb:   # MongoDB database
  weaviate:  # Vector database
```

Same `docker-compose.yml` for dev and prod.

### 10.2 Hosting: Local first, Cloud later

- Development: Docker Compose on local machine (free)
- Production: Cloud choice deferred (DigitalOcean, Hetzner, AWS, etc.)

### 10.3 CI/CD: GitHub Actions CI + Manual deploy

- GitHub Actions: auto-run tests on every push (free, 2000 min/month)
- Manual deploy: `ssh + git pull + docker compose up -d`

---

## Project Structure

```
reqruit/
├── pyproject.toml
├── .env.example
├── CLAUDE.md
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── middleware/
│   │   └── routes/
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── mongodb.py
│   │   ├── weaviate.py
│   │   └── documents/
│   ├── repositories/
│   ├── services/
│   ├── llm/
│   │   ├── manager.py
│   │   ├── providers/
│   │   ├── circuit_breaker.py
│   │   └── cost_tracker.py
│   ├── agents/
│   ├── workflows/
│   │   ├── states/
│   │   ├── graphs/
│   │   └── checkpointer.py
│   ├── rag/
│   │   ├── embeddings.py
│   │   ├── chunker.py
│   │   └── retriever.py
│   └── guardrails/
│       ├── input_validator.py
│       ├── output_validator.py
│       └── pii_detector.py
├── migrations/
├── tests/
└── docker/
    ├── Dockerfile
    ├── docker-compose.yml
    └── docker-compose.dev.yml
```

---

## Decision Log (Complete)

| Date | Module | Decision | Rationale |
|------|--------|----------|-----------|
| 2026-02-03 | Foundation | uv | 10-100x faster, future-proof |
| 2026-02-03 | Foundation | Hybrid Structure | Layers for infra, domains for AI |
| 2026-02-03 | Foundation | Pydantic Settings | Type-safe, FastAPI integration |
| 2026-02-03 | Foundation | Full Async | I/O bound workload |
| 2026-02-16 | Database | ~~SQLAlchemy~~ -> Beanie | Async ODM, Pydantic-native |
| 2026-02-16 | Database | ~~PostgreSQL+pgvector~~ -> MongoDB+Weaviate | Flexible documents + dedicated vector search |
| 2026-02-16 | Database | ~~Alembic~~ -> Schema-less + scripts | MongoDB best practice |
| 2026-02-16 | Database | Hybrid document design | Embed small, reference large |
| 2026-02-03 | Database | Repository Pattern | Testability, separation |
| 2026-02-03 | LLM | Hybrid Abstraction | LangChain + custom wrapper |
| 2026-02-03 | LLM | Task-based Routing | Explicit, no guessing |
| 2026-02-03 | LLM | Circuit Breaker | Production resilience |
| 2026-02-03 | LLM | Real-time Budgets | Cost control |
| 2026-02-16 | LLM | Groq Free Fallback | 500K tokens/day free |
| 2026-02-03 | Agents | Workflow-First | Start simple, evolve later |
| 2026-02-03 | Agents | LangGraph | Checkpoints, HITL, production-ready |
| 2026-02-03 | Agents | Specialized Agents (13) | Focused, testable |
| 2026-02-16 | Agents | MongoDB Checkpoints | Same store as operational data |
| 2026-02-03 | Agents | Approval Gates | User control on critical actions |
| 2026-02-16 | Memory | Summarization | Compress older messages |
| 2026-02-16 | Memory | Hybrid Storage | MongoDB structured + Weaviate semantic |
| 2026-02-16 | Memory | Per-Agent Retrieval | Tailored recipe per agent |
| 2026-02-16 | RAG | Hybrid Chunking | Document-aware + fixed fallback |
| 2026-02-16 | RAG | BGE-small-en-v1.5 | Free, local, good quality |
| 2026-02-16 | RAG | Hybrid+Filtered Search | Semantic + keyword + metadata |
| 2026-02-16 | API | JWT (Access+Refresh) | Stateless, scalable |
| 2026-02-16 | API | SSE + REST | Streaming output + discrete actions |
| 2026-02-16 | API | No Versioning | Single consumer, learning project |
| 2026-02-16 | Guardrails | Layered Input | Pydantic + Rules + OpenAI + LlamaGuard |
| 2026-02-16 | Guardrails | Schema+Rules+Self-Check | Groq 8B on critical outputs |
| 2026-02-16 | Evaluation | LangSmith + Custom Logging | Dev tracing + prod metrics |
| 2026-02-16 | Evaluation | Layered Testing | Unit + Eval + Integration |
| 2026-02-16 | Deployment | Docker Compose | Same config dev/prod |
| 2026-02-16 | Deployment | Local first, cloud later | Free during development |
| 2026-02-16 | Deployment | GitHub Actions CI | Auto-test, manual deploy |
