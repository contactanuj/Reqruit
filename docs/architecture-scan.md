# Reqruit — Architecture Document (Deep Scan)

> Complete architecture reference generated from deep source code analysis for AI-assisted development.

**Generated**: 2026-03-14 | **Scan Level**: Deep

---

## 1. System Architecture (7 Layers)

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 7: API (FastAPI routes, middleware, dependencies)        │
│  Entry: src/api/main.py → create_app()                          │
│  7 route modules, CORS, request logging, exception handlers     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 6: Services (business logic orchestration)               │
│  IndexingService (RAG write path), MetricsService (cost/budget) │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: Agents + Workflows (LangGraph state machines)         │
│  6 agents, 1 workflow graph, HITL interrupt/resume              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: LLM Provider (routing, circuit breaker, cost)         │
│  ModelManager → Anthropic | OpenAI | Groq (12 task types)       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: RAG + Memory (embeddings, retrieval, chunking)        │
│  BGE-small-en-v1.5 (384d), Weaviate hybrid, MemoryRecipes       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Repositories (data access, owner-scoping)             │
│  BaseRepository[T] (MongoDB) + WeaviateRepository (vector)      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Database (MongoDB 7 + Weaviate 1.28.4)                │
│  14 MongoDB collections, 4 Weaviate collections                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Application Startup Sequence

```
create_app()
  ├── Register exception handlers (AppError, InvalidId)
  ├── Add CORS middleware
  ├── Add RequestLoggingMiddleware
  ├── Register 7 route modules
  └── Lifespan startup:
      1. configure_logging(is_development)
      2. connect_mongodb(settings)        → 14 Beanie models registered
      3. connect_weaviate(settings)       → 4 collections ensured
      4. init_embeddings(settings)        → BGE model loaded (~2-3s)
      5. init_model_manager(settings)     → LLM routing ready
      6. init_checkpointer(settings)      → MongoDBSaver for LangGraph
      7. init_cover_letter_graph()        → Compiled workflow graph
      Lifespan shutdown: reverse order teardown
```

---

## 3. Agent Architecture (6 Agents)

| Agent | Task Type | Primary LLM | Temp | Purpose |
|-------|-----------|-------------|------|---------|
| RequirementsAnalyst | DATA_EXTRACTION | GPT-4o-mini | 0.0 | Extract structured requirements from JD |
| CoverLetterWriter | COVER_LETTER | Claude Sonnet | 0.7 | Write tailored cover letters |
| BehavioralQuestionGenerator | INTERVIEW_PREP | Claude Sonnet | 0.5 | Generate 5-8 behavioral questions |
| MockInterviewer | MOCK_INTERVIEW | Claude Sonnet | 0.7 | Evaluate STAR answers, score 1-10 |
| MockInterviewSummarizer | MOCK_INTERVIEW | Claude Sonnet | 0.7 | Summarize session, overall score |
| OutreachComposer | OUTREACH_MESSAGE | Claude Sonnet | 0.7 | Personalized networking messages |

All inherit from `BaseAgent`: `build_messages()` → `__call__()` → `process_response()`

---

## 4. Workflow: Cover Letter (LangGraph)

```
START → analyze_requirements → retrieve_memories → write_cover_letter → human_review → END
                                                           ↑                    │
                                                           └── revise (feedback)┘
```

- **HITL**: `interrupt()` pauses execution, SSE streams to client
- **Persistence**: MongoDBSaver checkpoints (survive restarts)
- **State**: CoverLetterState TypedDict (messages, job_description, resume_text, requirements_analysis, memory_context, cover_letter, feedback, status)

---

## 5. LLM Provider Layer

### Routing: 12 Task Types → 3 Providers

| Task | Primary | Fallback |
|------|---------|----------|
| COVER_LETTER | Claude Sonnet ($3/$15 per M) | Groq Llama 70B (free) |
| DATA_EXTRACTION | GPT-4o-mini ($0.15/$0.60) | Groq Llama 70B (free) |
| INTERVIEW_PREP | Claude Sonnet | Groq Llama 70B |
| MOCK_INTERVIEW | Claude Sonnet | Groq Llama 70B |
| OUTREACH_MESSAGE | Claude Sonnet | Groq Llama 70B |
| QUICK_CHAT | Claude Haiku ($0.80/$4) | Groq Llama 8B |

### Circuit Breaker: CLOSED →(3 failures)→ OPEN →(60s)→ HALF_OPEN →(success)→ CLOSED

---

## 6. RAG Pipeline

### Write Path: IndexingService
```
Document → Chunk (section-aware/fixed-size) → Embed (BGE 384d) → Store (Weaviate)
```

### Read Path: Memory Retrieval
```
Query → Embed → Weaviate hybrid_search (BM25 + vector, α=0.7) → Rank → Format → Inject into prompt
```

### Per-Agent Memory Recipes

| Agent | Weaviate % | MongoDB % | Collections |
|-------|-----------|-----------|-------------|
| requirements_analyst | 80% | 20% | ResumeChunk, JobEmbedding |
| cover_letter_writer | 70% | 30% | ResumeChunk, CoverLetterEmbedding |

---

## 7. Guardrails

### Input: Pydantic → Rules → OpenAI Moderation (fail-open)
### Output: Schema → Rules (PII, tone, length) → Groq self-check (free, fail-open)

---

## 8. Authentication

- **Access token**: JWT HS256, 15 min, stateless
- **Refresh token**: JWT HS256, 7 days, stored in MongoDB with family_id
- **Rotation**: Each refresh revokes old token, issues new pair
- **Theft detection**: Reuse of revoked token revokes entire family

---

## 9. Application Status Machine

```
SAVED → APPLIED → INTERVIEWING → OFFERED → ACCEPTED
  ↓        ↓           ↓            ↓
WITHDRAWN REJECTED   REJECTED    REJECTED
```

All terminal states are archived. Transitions validated server-side.

---

## 10. Data Architecture

- **MongoDB**: 14 collections (users, profiles, resumes, jobs, companies, contacts, applications, documents, outreach_messages, interviews, star_stories, llm_usage, mock_sessions, refresh_tokens)
- **Weaviate**: 4 collections (ResumeChunk, JobEmbedding, CoverLetterEmbedding, STARStoryEmbedding)
- **Patterns**: Repository pattern, owner scoping, multi-tenancy (Weaviate), denormalization, atomic versioning, two-query (avoid N+1)
