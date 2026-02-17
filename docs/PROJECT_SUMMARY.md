# Reqruit - Complete Project Summary

> **Document Purpose:** This is the comprehensive summary of all design discussions, decisions, and architectural choices made for the Reqruit project. This document serves as the canonical reference and will be updated as the project evolves.

> **Last Updated:** 2026-02-17

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Learning Objectives](#2-learning-objectives)
3. [Module 1: Project Foundation](#3-module-1-project-foundation)
4. [Module 2: Database Layer](#4-module-2-database-layer)
5. [Module 3: LLM Provider Layer](#5-module-3-llm-provider-layer)
6. [Module 4: Agent Architecture](#6-module-4-agent-architecture)
7. [Application Blueprint](#7-application-blueprint)
8. [Technical Architecture](#8-technical-architecture)
9. [Module 5: Memory Systems](#9-module-5-memory-systems)
10. [Module 6: RAG Pipeline](#10-module-6-rag-pipeline)
11. [Module 7: API Layer](#11-module-7-api-layer)
12. [Module 8: Guardrails](#12-module-8-guardrails)
13. [Module 9: Evaluation](#13-module-9-evaluation)
14. [Module 10: Deployment](#14-module-10-deployment)
15. [Key Discussion Highlights](#15-key-discussion-highlights)
16. [Decision Log](#16-decision-log)

---

## 1. Project Overview

### What We're Building

**Reqruit** - An AI-powered job hunting assistant that helps users through the entire job search lifecycle: from profile creation to application tracking.

### Why This Project?

The user wanted to build a **comprehensive agentic AI project** to learn production-grade patterns. After considering multiple options (AI Dungeon Master, Bug Bounty Hunter, etc.), we selected Reqruit because:

- **Practical & Useful:** Solves a real problem the user faces
- **Limited Scope:** Focused enough to complete, comprehensive enough to learn
- **Rich in AI Patterns:** Covers all 12+ agentic AI concepts
- **Multi-stage Workflows:** Natural fit for agent orchestration
- **RAG Requirements:** Resume parsing, job matching, document generation
- **Human-in-the-Loop:** Critical for job applications (user must approve)

### Core Tech Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Language | Python 3.11+ | Industry standard for AI/ML |
| API Framework | FastAPI | Async-native, modern, great DX |
| Operational DB | MongoDB (Beanie ODM) | Flexible documents, Pydantic-native |
| Vector DB | Weaviate | Dedicated HNSW, free hybrid search |
| Agent Framework | LangGraph | Production-grade, checkpoints, HITL |
| LLM Providers | Multi-provider | Anthropic, OpenAI, Google, Ollama |
| Package Manager | uv | 10-100x faster than alternatives |

---

## 2. Learning Objectives

The project is designed to teach these production-grade agentic AI concepts:

| # | Concept | Where It's Applied |
|---|---------|-------------------|
| 1 | **LangGraph** | Workflow orchestration, state machines |
| 2 | **LangSmith** | Observability, tracing, evaluation |
| 3 | **Database Design** | MongoDB documents + Weaviate vectors |
| 4 | **Context Management** | Conversation state, workflow state |
| 5 | **Short-term Memory** | LangGraph messages, sliding window |
| 6 | **Long-term Memory** | MongoDB collections + Weaviate embeddings |
| 7 | **Evaluation Criteria** | Quality metrics, golden datasets |
| 8 | **Guardrails** | Input/output validation, PII detection |
| 9 | **Chain of Thought** | Structured reasoning in agents |
| 10 | **Model Selection** | Task-based routing, cost optimization |
| 11 | **RAG** | Resume chunks, job embeddings, retrieval |
| 12 | **Human-in-the-Loop** | Approval gates before critical actions |

---

## 3. Module 1: Project Foundation

### 1.1 Package Manager

**Decision:** ✅ **uv**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Poetry** | Standard, well-documented, lockfile | Slow installs (180s for our stack) |
| **uv** | 10-100x faster, Rust-based, future-proof | Newer, less documentation |
| **pip + requirements.txt** | Universal, simple | No lockfile, no dependency resolution |

**Why uv:**
- 10-100x faster installs (8s vs 180s for our stack)
- Lower CI/CD costs due to faster builds
- Major companies adopting it (future-proof)
- Compatible with pyproject.toml (not locked in)
- Better developer experience during experimentation

**Discussion Highlight:** We had a detailed comparison of Poetry vs uv. Poetry is the current "safe" choice, but uv's speed benefits are significant for development iteration and CI/CD costs.

---

### 1.2 Project Structure Pattern

**Decision:** ✅ **Hybrid (Layer-based + Domain-based)**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Flat** | Simple | Doesn't scale |
| **Domain-driven** | Business-focused | Can be confusing for infra |
| **Layer-based** | Clear technical separation | AI components get scattered |
| **Hybrid** | Best of both | Slightly more complex |

**Why Hybrid:**
- Layers for infrastructure (api, db, core, services)
- Domains for AI components (agents, memory, retrieval, guardrails)
- Reflects the natural structure of an agentic AI system
- Scales well as complexity grows
- Easy to navigate and understand

**Resulting Structure:**
```
src/
├── api/           # Layer: FastAPI routes
├── core/          # Layer: Config, security
├── db/            # Layer: Beanie documents
├── repositories/  # Layer: Data access
├── services/      # Layer: Business logic
├── llm/           # Domain: Provider management
├── agents/        # Domain: AI agents
├── workflows/     # Domain: LangGraph workflows
├── rag/           # Domain: Embeddings, retrieval
└── guardrails/    # Domain: Validation, safety
```

---

### 1.3 Configuration Management

**Decision:** ✅ **Pydantic Settings**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Pydantic Settings** | Type-safe, validation, IDE support | Requires Pydantic knowledge |
| **python-decouple** | Simple, .env focused | No type safety |
| **Dynaconf** | Feature-rich, multi-env | Overkill, extra dependency |
| **Custom** | Full control | Reinventing the wheel |

**Why Pydantic Settings:**
- Type safety with IDE autocomplete
- Validation at startup (fail fast)
- Already using Pydantic for FastAPI schemas
- Works seamlessly with .env files
- No additional dependencies needed

---

### 1.4 Async Strategy

**Decision:** ✅ **Full Async**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Full async** | Best for I/O bound work | Requires async everywhere |
| **Sync with async endpoints** | Simpler business logic | Misses concurrency benefits |
| **Mixed** | Flexible | Inconsistent, debugging harder |

**Why Full Async:**
- Our app is heavily I/O bound (LLM calls, DB queries, vector search)
- FastAPI + Beanie (async MongoDB ODM) + httpx all support async natively
- LangGraph supports async execution
- Better concurrent user handling
- Modern Python best practice for web services

---

## 4. Module 2: Database Layer (Revised)

### Decision Evolution

This module went through significant discussion and a late revision:
1. **Initially chosen:** PostgreSQL + pgvector (all-in-one)
2. **User reconsidered:** Wanted MongoDB for schema flexibility during active development
3. **Final decision:** MongoDB + Weaviate (after detailed tradeoff analysis)

---

### 2.1 ODM Choice

**Decision:** ✅ **Beanie (async MongoDB ODM)**

**Previous Decision:** SQLAlchemy 2.0 (changed due to MongoDB switch)

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Beanie** | Async-native, Pydantic models = DB documents | Newer, smaller ecosystem |
| **MongoEngine** | Mature, large community | Synchronous only (violates Full Async) |
| **Raw PyMongo async** | Maximum flexibility, official async driver | More boilerplate, no ODM benefits |
| **ODMantic** | Pydantic-based like Beanie | Less mature, smaller community |

**Why Beanie:**

- Beanie 2.0 uses PyMongo's native async API directly (not Motor as in 1.x) — aligns with our Full Async decision
- Documents ARE Pydantic models — one definition for API schema + DB document + validation
- Seamless FastAPI integration (shared Pydantic models)
- Repository Pattern maps cleanly to Beanie's document methods
- Active community, growing adoption

**Note:** As of Beanie 2.0, the Motor dependency was removed in favor of PyMongo's built-in async API. We interact with Beanie, not PyMongo directly.

---

### 2.2 Database Architecture

**Decision:** ✅ **MongoDB + Weaviate**

**Previous Decision:** PostgreSQL + pgvector

**Discussion History:**
This was the most debated decision. The user initially asked about MongoDB, we recommended PostgreSQL + pgvector for simplicity. User later reconsidered due to schema flexibility needs during active development. Final decision: MongoDB + Weaviate.

**Architecture:**
```
MongoDB (operational data)     Weaviate (vector search)
├── users                      ├── ResumeChunks
├── profiles                   ├── JobEmbeddings
├── resumes                    ├── CoverLetterEmbeddings
├── jobs                       └── STARStoryEmbeddings
├── companies
├── contacts
├── applications
├── documents
├── outreach_messages
├── interviews
├── star_stories
├── llm_usage
└── workflow_checkpoints
```

**Technical Justification (Interview-ready):**
- **MongoDB:** Semi-structured data from multiple sources (job listings from different boards have varying fields). Document model handles this natively. Beanie + Pydantic gives one model definition for API + DB + validation.
- **Weaviate:** Purpose-built vector DB with dedicated HNSW indexing, built-in hybrid search (BM25 + vector) for free, metadata filtering. Separation of concerns: operational data scales differently than semantic search.
- **Together:** Each technology does what it's best at. MongoDB for flexible document storage, Weaviate for optimized vector operations.

**Weaviate Setup:**
- Local dev: Docker container (self-hosted)
- Production: Weaviate Cloud Services (WCS)

**Weaviate Features Used (All Free):**
- Vector search (cosine similarity)
- Hybrid search (BM25 + vector combined)
- Metadata filtering (location, salary, remote)
- Multi-tenancy (per-user data isolation)

**Weaviate Features Skipped:**
- text2vec-openai (API cost — we do app-side embeddings instead)
- Generative module (we have our own LLM layer)

**Embedding Strategy:** App-side generation
- We generate embeddings in our application code
- Store raw vectors in Weaviate
- Full control over embedding model (can use free local models)
- No vendor lock-in to OpenAI for embeddings

**Honest Tradeoffs vs PostgreSQL + pgvector:**
| Aspect | MongoDB + Weaviate | PostgreSQL + pgvector |
|--------|-------------------|----------------------|
| Infrastructure | 3 services (app + mongo + weaviate) | 2 services (app + postgres) |
| Cross-store consistency | Manual (no transactions across stores) | ACID across all data |
| Vector search quality | Better (dedicated HNSW, hybrid search) | Good (shared resources) |
| Schema flexibility | Native | Via JSONB columns |
| Operational complexity | Higher | Lower |
| Learning value | Higher (two technologies) | Lower |

---

### 2.3 Migration Strategy

**Decision:** ✅ **Schema-less + Application Defaults + Migration Scripts**

**Previous Decision:** Alembic (no longer applicable — Alembic is SQLAlchemy-only)

**Approach (Industry standard for MongoDB — used at Uber, Lyft, MongoDB Inc.):**
1. Beanie documents define defaults for new fields
2. Application code handles missing fields gracefully (Optional types, default values)
3. Data transformation scripts for rare breaking changes
4. `schema_version` field on documents for version tracking

---

### 2.4 Document Design Pattern

**Decision:** ✅ **Hybrid (Embedded + References)**

**Rules:**
- **Embed** when: data is tightly coupled, always accessed together, small
  - Example: `skills` list inside `profiles`, `requirements` inside `jobs`
- **Reference** when: data is independent, queried separately, large
  - Example: `applications` reference `jobs` and `users` by ObjectId

---

### 2.5 Data Access Pattern

**Decision:** ✅ **Repository Pattern** (unchanged from original)

**Why Repository Pattern:**
- Clean separation between data access and business logic
- Easy to mock for unit testing
- Works cleanly with Beanie documents
- Services stay focused on orchestration

---

## 5. Module 3: LLM Provider Layer

### 3.1 Provider Abstraction Pattern

**Decision:** ✅ **Hybrid (LangChain + Custom Wrapper)**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Strategy Pattern (Custom)** | Full control | Must maintain each provider |
| **LangChain Native** | Already built, maintained | Less control |
| **Hybrid** | LangChain reliability + our control | Two abstraction layers |

**Why Hybrid:**
- LangChain already solved the "talk to 20 different LLM APIs" problem
- We add our own routing logic, cost tracking, and fallback behavior
- LangGraph (which we use for agents) expects LangChain models
- Best of both: reliability + control

**Implementation Pattern:**
```python
class ModelManager:
    def __init__(self, config: LLMConfig):
        self.providers = {
            "anthropic": ChatAnthropic(...),
            "openai": ChatOpenAI(...),
            "ollama": ChatOllama(...),
        }
        self.router = ModelRouter(config)
        self.cost_tracker = CostTracker()
```

---

### 3.2 Model Routing Strategy

**Decision:** ✅ **Task-based Routing**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Config-based** | Simple | Same model for everything |
| **Task-based** | Right model for each job | Must define task types |
| **Cost-based** | Optimizes spend | Hard to estimate complexity |
| **Adaptive** | Learns over time | Requires training data |

**Why Task-based:**
- Explicit mapping: task type → optimal model
- No guessing or heuristics needed
- Cost optimization built into task definitions
- Easy to tune based on experience

**Discussion Highlight:** User asked how cost-based routing calculates "complexity score." Explained that it requires either:
1. Heuristics (inaccurate)
2. Classifier model (ironic - LLM call to decide which LLM)
3. Historical learning (complex infrastructure)

Task-based routing avoids these problems by having the developer explicitly declare what each task needs.

**Example Routing:**
| Task | Model | Reason |
|------|-------|--------|
| Resume Analysis | claude-sonnet-4-20250514 | Deep reasoning required |
| Cover Letter | claude-sonnet-4-20250514 | Creative writing |
| Quick Chat | claude-haiku | Speed, low cost |
| Data Extraction | gpt-4o-mini | Good at structured JSON |

---

### 3.3 Fallback Strategy

**Decision:** ✅ **Circuit Breaker**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Simple chain** | Easy to implement | Keeps trying failed providers |
| **Circuit breaker** | Skips known-broken providers | More complex |
| **Load balancing** | Distributes load | Overkill for our scale |

**Why Circuit Breaker:**
- Skips known-broken providers (no wasted timeouts)
- Automatic recovery when service returns
- Prevents cascading failures
- Industry-standard resilience pattern

**How It Works:**
- Track failures per provider
- After N failures, mark provider as "open" (unavailable)
- After recovery time, try again ("half-open")
- If successful, mark as "closed" (available)

---

### 3.4 Cost Tracking

**Decision:** ✅ **Real-time Budgets**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Per-request logging** | Basic visibility | No aggregation |
| **Aggregated metrics** | Track totals | No enforcement |
| **Real-time budgets** | Prevents runaway costs | Most complex |

**Why Real-time Budgets:**
- Per-request logging for visibility
- Aggregated metrics per user/agent
- Spending limits prevent runaway costs
- Essential for production LLM applications

---

## 6. Module 4: Agent Architecture

### Application Approach

**Decision:** ✅ **Workflow-First** (with future Hybrid option)

**Discussion:** This was a major architectural decision. We discussed three approaches:

| Approach | Description | Complexity |
|----------|-------------|------------|
| **Workflow-First** | Guided stages, structured UI | Lower |
| **Chatbot-First** | Open-ended conversation | Higher |
| **Hybrid** | Conversation + structured workflows | Medium |

**Challenges with Chatbot-First (identified by user):**
1. Multiple intent analysis - One query can have multiple intents
2. Dynamic intent selection - No fixed order
3. Dynamic agent calls - Need to determine call order from intents
4. Memory management - When to persist vs. just use in context
5. UI feedback - How to show profile updates in real-time

**Why Workflow-First:**
- Start simple, evolve as needed
- Clear user journey through 5 stages
- Easier to build, test, and debug
- Can add conversational layer later (Hybrid)
- Avoids complex intent parsing initially

---

### 4.1 Agent Framework

**Decision:** ✅ **LangGraph**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **LangGraph** | State machines, checkpoints, HITL | Learning curve |
| **LangChain Agents** | Simple to start | Linear only, no cycles |
| **AutoGen** | Multi-agent focus | Microsoft ecosystem |
| **CrewAI** | Role-based teams | Less flexible |
| **Custom** | Full control | Reinventing the wheel |

**Why LangGraph:**
- State machines with cycles/loops (job hunting has natural cycles)
- Built-in persistence & checkpoints (users can pause/resume)
- Human-in-the-loop support (critical for job applications)
- Production-ready (from LangChain team)
- Each workflow stage = one subgraph

---

### 4.2 Agent Design Pattern

**Decision:** ✅ **Specialized Agents per Workflow**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **Single mega-agent** | Simple | Hard to debug, test |
| **Specialized agents** | Focused, testable | Need coordination |
| **Hierarchical** | Dynamic delegation | Extra LLM calls |
| **Collaborative** | Peer-to-peer | Complex interactions |

**Why Specialized Agents:**
- Each agent has one focused job
- Easy to test independently
- Different agents can use different models (cost optimization)
- LangGraph connects them via shared state
- Clear responsibility boundaries

**Agents by Workflow:**
| Workflow | Agents |
|----------|--------|
| Profile Setup | ResumeParser, EntityExtractor, ProfileEnhancer |
| Job Discovery | JobSearcher, JobMatcher, CompanyResearcher, POCFinder |
| Application | ResumeTailor, CoverLetterWriter, OutreachComposer |
| Interview Prep | CompanyBrief, QuestionGenerator, STARHelper, MockInterviewer |

---

### 4.3 State Management

**Decision:** ✅ **Persistent Checkpoints (MongoDB)** (Revised)

**Discussion:** This was a deep-dive topic. We explored how different types of "memory" map to technical implementations.

**Memory Layers Defined:**
| Layer | Concept | Storage | Lifespan |
|-------|---------|---------|----------|
| **Conversation** | Chat history | LangGraph messages | Session |
| **Workflow** | Agent outputs, progress | LangGraph checkpoints → MongoDB | Days/weeks |
| **Knowledge** | Permanent user data | MongoDB collections | Permanent |
| **Semantic** | Embeddings for RAG | Weaviate | Permanent |

**Why MongoDB Checkpoints:**
- Job hunting spans days/weeks (need persistence)
- Users can pause and resume workflows
- Survives server restarts
- LangGraph's `MongoDBSaver` (`langgraph-checkpoint-mongodb`) works with our MongoDB
- Keeps all operational data in one store
- Enables workflow rollback if needed

**Memory Decision Matrix:**
| Data Type | Action | Example |
|-----------|--------|---------|
| Profile changes | **PERSIST to DB** | "I now have 5 years Python experience" |
| Resume updates | **PERSIST to DB** | New tailored resume version |
| Draft documents | **CHECKPOINT** | Cover letter awaiting approval |
| One-off questions | **CONTEXT ONLY** | "What's Google's interview process?" |

---

### 4.4 Human-in-the-Loop

**Decision:** ✅ **Approval Gates**

**Options Considered:**
| Option | Pros | Cons |
|--------|------|------|
| **No HITL** | Fully autonomous | Risky for job apps |
| **Approval gates** | Control on critical actions | Adds friction |
| **Intervention points** | Human can jump in anytime | Complex to implement |

**Why Approval Gates:**
- Required before document finalization (cover letters, messages)
- Critical for job applications (don't send without approval)
- LangGraph has built-in `interrupt()` for this
- Balance of automation + user control

**HITL Points:**
- Resume tailoring → Approve before saving
- Cover letter → Approve before finalizing
- Outreach messages → Approve before marking ready
- Application submission → Confirm before status change

---

## 7. Application Blueprint

### Workflow Stages

```
STAGE 1        STAGE 2        STAGE 3        STAGE 4        STAGE 5
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ PROFILE │──▶│DISCOVER │──▶│  APPLY  │──▶│ PREPARE │──▶│  TRACK  │
│  SETUP  │   │  JOBS   │   │         │   │         │   │         │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### Feature Map

**Stage 1: Profile Setup**
| Feature | Description | Agents |
|---------|-------------|--------|
| Resume Upload | PDF/DOCX parsing | ResumeParser |
| Entity Extraction | Skills, experience, education | EntityExtractor |
| Profile Enhancement | Career goals, preferences | ProfileEnhancer |
| Embedding Generation | For semantic matching | (automatic) |

**Stage 2: Discover Jobs**
| Feature | Description | Agents |
|---------|-------------|--------|
| Job Search | Manual entry, URL paste | JobSearcher |
| Job Matching | Semantic similarity + preferences | JobMatcher |
| Company Research | Culture, tech stack, news | CompanyResearcher |
| POC Discovery | Find LinkedIn contacts by role | POCFinder |

**Stage 3: Apply**
| Feature | Description | Agents |
|---------|-------------|--------|
| Resume Tailoring | Highlight relevant experience per JD | ResumeTailor |
| Cover Letter | Personalized, company-aware | CoverLetterWriter |
| Outreach Messages | Role-specific (recruiter/engineer/manager) | OutreachComposer |
| Approval Gates | Human review before finalization | (LangGraph interrupt) |

**Stage 4: Prepare**
| Feature | Description | Agents |
|---------|-------------|--------|
| Company Brief | Deep-dive research document | CompanyBrief |
| Question Generation | Behavioral + technical | QuestionGenerator |
| STAR Story Bank | Structured behavioral examples | STARHelper |
| Mock Interview | AI plays interviewer | MockInterviewer |

**Stage 5: Track**
| Feature | Description | Implementation |
|---------|-------------|----------------|
| Pipeline Dashboard | Kanban (Saved → Applied → Interview → Offer) | UI + MongoDB |
| Calendar Integration | Interview scheduling | Google Calendar API |
| Follow-up Reminders | Automated nudges | Background jobs |
| Analytics | Response rates, conversion | Aggregation queries |

---

## 8. Technical Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Future)                           │
│                       React/Next.js + SSE                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                         │
│  Routes: auth, profile, jobs, applications, documents, interviews   │
│  SSE: /stream (real-time agent output) + REST (user actions)        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   SERVICE LAYER     │ │    AGENT LAYER      │ │  WORKFLOW ENGINE    │
│ ProfileService      │ │ ResumeAnalyzer      │ │ LangGraph           │
│ JobService          │ │ JobMatcher          │ │ State Management    │
│ ApplicationService  │ │ CoverLetterWriter   │ │ Checkpointing       │
│ DocumentService     │ │ InterviewPrepper    │ │ Human-in-Loop       │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM PROVIDER LAYER                             │
│  ModelManager: Task-based routing, Circuit breaker, Cost tracking   │
│  Providers: Anthropic, OpenAI, Google, Ollama                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│       MongoDB (Beanie)          │ │       Weaviate                  │
│  Operational data + Checkpoints │ │  Vector search + Hybrid search  │
│  ├── users, profiles            │ │  ├── ResumeChunks               │
│  ├── resumes, jobs, companies   │ │  ├── JobEmbeddings              │
│  ├── applications, documents    │ │  ├── CoverLetterEmbeddings      │
│  ├── interviews, star_stories   │ │  └── STARStoryEmbeddings        │
│  └── llm_usage, checkpoints    │ │                                  │
└─────────────────────────────────┘ └─────────────────────────────────┘
```

### Data Schema

**MongoDB Collections:**

| Collection | Purpose | Key Fields | Design |
|------------|---------|------------|--------|
| users | Authentication | id, email, hashed_password | Standalone |
| profiles | User career data | skills[], preferences{}, target_roles[] | Ref → users |
| resumes | Resume documents | raw_text, parsed_data{}, version, is_master | Ref → users |
| jobs | Job listings | title, description, requirements{}, salary{} | Ref → companies |
| companies | Company info | name, culture_notes, tech_stack[], research{} | Standalone |
| contacts | LinkedIn POCs | name, role, linkedin_url, contacted | Ref → companies |
| applications | Pipeline items | status, match_score, applied_at | Ref → users, jobs |
| documents | Generated docs | type, content, version, is_approved | Ref → applications |
| outreach_messages | LinkedIn messages | message_type, content, is_sent | Ref → applications, contacts |
| interviews | Interview records | scheduled_at, type, notes{}, questions[] | Ref → applications |
| star_stories | Behavioral examples | situation, task, action, result, tags[] | Ref → users |
| llm_usage | Cost tracking | agent, model, tokens, cost, timestamp | Ref → users |

**Weaviate Classes (Vector Store):**

| Class | Purpose | Properties | Vectors From |
|-------|---------|------------|-------------|
| ResumeChunk | Resume sections for RAG | content, chunk_type, resume_id, user_id | App-side embedding |
| JobEmbedding | Job description vectors | title, description_summary, job_id | App-side embedding |
| CoverLetterEmbedding | Past cover letters for reuse | content_summary, company, role, doc_id | App-side embedding |
| STARStoryEmbedding | Behavioral stories for retrieval | story_summary, tags, story_id | App-side embedding |

### Project Structure

```
reqruit/
├── pyproject.toml                 # uv config
├── .env.example                   # Environment template
│
├── src/
│   ├── api/                       # FastAPI layer
│   │   ├── main.py                # App entry point
│   │   ├── dependencies.py        # DI container
│   │   ├── middleware/            # Auth, logging
│   │   └── routes/                # Endpoint handlers
│   │
│   ├── core/                      # Core utilities
│   │   ├── config.py              # Pydantic Settings
│   │   ├── security.py            # JWT, hashing
│   │   └── exceptions.py          # Custom exceptions
│   │
│   ├── db/                        # Database layer
│   │   ├── mongodb.py             # Beanie init + connection setup
│   │   ├── weaviate.py            # Weaviate client setup
│   │   └── documents/             # Beanie document models
│   │       ├── user.py
│   │       ├── profile.py
│   │       ├── resume.py
│   │       ├── job.py
│   │       └── ...
│   │
│   ├── repositories/              # Data access (Repository Pattern)
│   │   ├── base.py                # Generic CRUD
│   │   └── [entity]_repo.py       # Entity-specific queries
│   │
│   ├── services/                  # Business logic
│   │   └── [domain]_service.py    # Orchestration layer
│   │
│   ├── llm/                       # LLM Provider Layer
│   │   ├── manager.py             # ModelManager
│   │   ├── providers/             # Provider implementations
│   │   ├── circuit_breaker.py     # Resilience
│   │   └── cost_tracker.py        # Usage tracking
│   │
│   ├── agents/                    # AI Agents
│   │   ├── base.py                # Base agent class
│   │   └── [name]_agent.py        # Specialized agents
│   │
│   ├── workflows/                 # LangGraph Workflows
│   │   ├── states/                # TypedDict state definitions
│   │   ├── graphs/                # Workflow graph definitions
│   │   └── checkpointer.py        # MongoDBSaver setup
│   │
│   ├── rag/                       # RAG Pipeline
│   │   ├── embeddings.py          # App-side embedding generation
│   │   ├── chunker.py             # Document chunking
│   │   └── retriever.py           # Weaviate search client
│   │
│   └── guardrails/                # Safety & Validation
│       ├── input_validator.py     # Input sanitization
│       ├── output_validator.py    # Output checking
│       └── pii_detector.py        # PII detection
│
├── migrations/                    # Custom MongoDB migration scripts
├── tests/                         # Test suite
└── docker/
    ├── Dockerfile
    ├── docker-compose.yml         # App + MongoDB + Weaviate
    └── docker-compose.dev.yml
```

---

## 9. Module 5: Memory Systems

### 5.1 Short-term Memory

**Decision:** ✅ **Summarization (Hybrid)**

- Keep last N messages verbatim (exact recent context)
- Summarize older messages (compress without losing key info)
- LangGraph custom message reducers handle this
- Prevents context window overflow on long workflows

### 5.2 Long-term Memory Storage

**Decision:** ✅ **Hybrid (MongoDB + Weaviate)**

| Data Type | Store | Why |
|-----------|-------|-----|
| User profile, preferences | MongoDB | Structured, direct lookup |
| Application history, outcomes | MongoDB | Structured, recency queries |
| Past cover letters (for reuse) | Weaviate | Semantic similarity search |
| STAR stories (for retrieval) | Weaviate | Match stories to interview questions |
| Resume chunks (for matching) | Weaviate | Semantic matching to JDs |
| Company research | MongoDB | Structured, freshness-based |

### 5.3 Memory Retrieval

**Decision:** ✅ **Hybrid (Recency + Relevance) — Per-Agent Tuning**

Each agent gets a tailored retrieval recipe. NOT the same for every agent.

| Agent | Relevance (Weaviate) | Recency (MongoDB) | Strategy |
|-------|---------------------|-------------------|----------|
| ResumeParser | 0% | 100% | Extraction only |
| ProfileEnhancer | 70% | 30% | Semantic skill matching |
| JobMatcher | 60% | 40% | Semantic + calibration |
| ResumeTailor | 70% | 30% | Match experience to JD |
| CoverLetterWriter | 50% | 50% | Similar letters + style |
| STARHelper | 90% | 10% | Pure semantic matching |
| OutreachComposer | 20% | 80% | Recent patterns |

**Rule:** "Most SIMILAR?" -> Relevance. "Most RECENT?" -> Recency. "Best for THIS?" -> Both.

---

## 10. Module 6: RAG Pipeline

### 6.1 Chunking Strategy

**Decision:** ✅ **Hybrid (Document-Aware + Fixed Fallback)**

- Document-aware for known formats (resumes, JDs) — each section = one chunk
- Fixed-size fallback (500 tokens, 50-token overlap) for unknown formats

### 6.2 Embedding Model

**Decision:** ✅ **BAAI/bge-small-en-v1.5** (via `langchain-huggingface`)

- Free, local, 384 dimensions
- Better quality than MiniLM (~40th vs ~60th on MTEB)
- No extra infrastructure needed
- Lock-in is moderate: re-embedding at our scale takes minutes

**Key findings:**
- Groq has NO embedding models (Feb 2026) — LLM inference only
- LLM lock-in is NONE (LangChain abstracts all providers)
- Embedding lock-in is MODERATE (change model = re-embed all vectors)

### 6.3 Search Strategy

**Decision:** ✅ **Hybrid + Filtered (Weaviate)**

- BM25 + vector combined with per-agent `alpha` tuning
- Metadata filters for user isolation, location, role type
- All free Weaviate features

---

## 11. Module 7: API Layer

### 7.1 Authentication

**Decision:** ✅ **JWT (Access + Refresh Tokens)**

- Access token: 15min, Refresh token: 7d with rotation
- Stateless — no DB lookup per request
- FastAPI has first-class JWT support

### 7.2 Real-time Updates

**Decision:** ✅ **SSE streaming + REST actions**

- SSE for one-way agent output streaming (token-by-token, progress events)
- REST for user actions (approve, reject, edit)
- LangGraph streaming naturally outputs tokens — SSE is the perfect fit

### 7.3 API Versioning

**Decision:** ✅ **No versioning** — single frontend, learning project

---

## 12. Module 8: Guardrails

### 8.1 Input Validation

**Decision:** ✅ **Layered (Pydantic + Rules + LLM Moderation)**

- Layer 1: Pydantic schema validation (automatic via FastAPI)
- Layer 2: Rule-based checks (PII regex, file type/size, length limits)
- Layer 3: LLM moderation on free-text fields only
  - OpenAI Moderation API (free, unlimited) + Llama Guard 3 via Groq (free tier)

### 8.2 Output Validation

**Decision:** ✅ **Schema + Content Rules + LLM Self-Check**

- Schema enforcement via `with_structured_output()` (free from LangChain)
- Rule-based content checks (PII regex, hallucination verification, tone)
- LLM self-check on critical outputs only (cover letters, outreach, tailored resumes)
- Self-check model: Groq Llama 3.1 8B (free, ~10-20 calls/day)

---

## 13. Module 9: Evaluation

### 9.1 Observability

**Decision:** ✅ **LangSmith + Custom Logging**

- **LangSmith** for development: auto-traces, visual explorer, eval datasets (free 5K/month)
- **Custom structlog** for production: cost aggregation, latency, error rates to MongoDB

### 9.2 Testing Strategy

**Decision:** ✅ **Layered (Unit + Eval Datasets + Integration)**

| Layer | What | When | Cost |
|-------|------|------|------|
| Unit (pytest + mocks) | Logic, schemas, guardrails | Every commit (CI) | Free |
| Eval datasets (LangSmith) | Agent output quality | Weekly | Free tier |
| Integration (real LLMs) | End-to-end critical paths | Manual | ~$0.50/run |

---

## 14. Module 10: Deployment

### 10.1 Containerization

**Decision:** ✅ **Docker Compose everywhere**

- Same `docker-compose.yml` for dev and prod
- Services: `app` (FastAPI) + `mongodb` + `weaviate`

### 10.2 Hosting

**Decision:** ✅ **Local first, Cloud choice later**

- Docker Compose on local machine during development (free)
- Cloud provider chosen when ready to deploy

### 10.3 CI/CD

**Decision:** ✅ **GitHub Actions CI + Manual deploy**

- Auto-run tests on every push (free, 2000 min/month)
- Manual deploy: `ssh + git pull + docker compose up -d`

---

## 15. Key Discussion Highlights

### Database Architecture: Three-Phase Decision

This was the most debated decision in the project, going through three phases:

**Phase 1: MongoDB vs PostgreSQL**
- User initially preferred MongoDB for familiarity and schema flexibility
- We recommended PostgreSQL + pgvector for simplicity (all-in-one, ACID, industry standard)
- Explained pgvector is PostgreSQL-only (can't combine with MongoDB)
- User agreed to PostgreSQL + pgvector

**Phase 2: Schema Flexibility Concern**
- User reconsidered: "I don't have complete DB structure ready, schema will change"
- We explained PostgreSQL handles this well via JSONB columns + Alembic migrations
- User was convinced and stayed with PostgreSQL

**Phase 3: Final Switch to MongoDB + Weaviate**
- User decided to switch to MongoDB + Weaviate for personal learning goals
- Acknowledged it's not the "simpler" choice but wanted hands-on experience
- We provided technical justification that holds up in interviews:
  - MongoDB: Semi-structured job data from varying sources, Pydantic-native ODM
  - Weaviate: Dedicated vector indexing, free hybrid search, separation of concerns
- Documented honest tradeoffs (higher operational complexity, no cross-store transactions)
- Updated all cascading decisions (ODM, migrations, checkpointing, project structure)

**Final Decision:** MongoDB (Beanie) + Weaviate

---

### Workflow vs Chatbot Architecture

**User's Concerns about Chatbot:**
1. Multiple intents in single query
2. Dynamic intent ordering
3. Complex agent orchestration
4. Memory management confusion
5. UI feedback complexity

**Resolution:**
- Provided detailed solutions for each challenge
- Showed how Hybrid approach would work
- User chose Workflow-First for simplicity
- Can evolve to Hybrid later

**Key Insight:** Workflow-First doesn't mean rigid. Users can navigate between stages freely. It just means each stage has a defined structure.

---

### Cost-Based vs Task-Based Routing

**User's Question:** How do you calculate "complexity score" for cost-based routing?

**Explanation:**
- Heuristics (length, keywords) are inaccurate
- Classifier model = extra LLM call (ironic)
- Historical learning = complex infrastructure

**Resolution:** Task-based routing avoids the problem entirely. Developer explicitly declares what each task needs based on domain knowledge.

---

## 16. Decision Log

| Date | Module | Decision | Rationale |
|------|--------|----------|-----------|
| 2026-02-03 | Foundation | uv | 10-100x faster, future-proof |
| 2026-02-03 | Foundation | Hybrid Structure | Layers for infra, domains for AI |
| 2026-02-03 | Foundation | Pydantic Settings | Type-safe, FastAPI integration |
| 2026-02-03 | Foundation | Full Async | I/O bound workload |
| 2026-02-16 | Database | ~~SQLAlchemy 2.0~~ -> Beanie | Async ODM, Pydantic-native, FastAPI seamless |
| 2026-02-16 | Database | ~~PostgreSQL + pgvector~~ -> MongoDB + Weaviate | Flexible documents + dedicated vector search |
| 2026-02-16 | Database | ~~Alembic~~ -> Schema-less + migration scripts | MongoDB best practice, industry standard |
| 2026-02-16 | Database | Hybrid document design | Embed small/coupled, reference large/independent |
| 2026-02-03 | Database | Repository Pattern | Testability, separation (unchanged) |
| 2026-02-03 | LLM | Hybrid Abstraction | LangChain + custom wrapper |
| 2026-02-03 | LLM | Task-based Routing | Explicit, no guessing |
| 2026-02-03 | LLM | Circuit Breaker | Production resilience |
| 2026-02-03 | LLM | Real-time Budgets | Cost control |
| 2026-02-16 | LLM | Groq Free Fallback | 500K tokens/day free for non-critical tasks |
| 2026-02-03 | Agents | Workflow-First | Start simple, evolve later |
| 2026-02-03 | Agents | LangGraph | Production patterns, checkpoints, HITL |
| 2026-02-03 | Agents | Specialized Agents (13) | Focused, testable |
| 2026-02-16 | Agents | ~~PostgreSQL~~ -> MongoDB Checkpoints | Same store as operational data |
| 2026-02-03 | Agents | Approval Gates | User control on critical actions |
| 2026-02-16 | Memory | Summarization | Compress older, keep recent verbatim |
| 2026-02-16 | Memory | Hybrid Storage (Mongo+Weaviate) | Structured + semantic recall |
| 2026-02-16 | Memory | Per-Agent Hybrid Retrieval | Tailored recipe per agent |
| 2026-02-16 | RAG | Hybrid Chunking | Document-aware + fixed fallback |
| 2026-02-16 | RAG | BGE-small-en-v1.5 | Free, local, good quality, low lock-in |
| 2026-02-16 | RAG | Hybrid+Filtered Search | Semantic + keyword + metadata, all free |
| 2026-02-16 | API | JWT (Access+Refresh) | Stateless, scalable, standard |
| 2026-02-16 | API | SSE + REST | Streaming output + discrete actions |
| 2026-02-16 | API | No Versioning | Single consumer, learning project |
| 2026-02-16 | Guardrails | Layered Input Validation | Pydantic + rules + OpenAI + LlamaGuard |
| 2026-02-16 | Guardrails | Schema+Rules+Self-Check | Groq 8B self-check on critical outputs |
| 2026-02-16 | Evaluation | LangSmith + Custom Logging | Dev tracing + prod metrics we control |
| 2026-02-16 | Evaluation | Layered Testing | Unit + Eval + Integration |
| 2026-02-16 | Deployment | Docker Compose everywhere | Same config dev/prod, personal tool |
| 2026-02-16 | Deployment | Local first, cloud later | Free during development |
| 2026-02-16 | Deployment | GitHub Actions CI + Manual deploy | Auto-test, manual control, free |

---

## Implementation Progress

| Module | Status | Date | Notes |
|--------|--------|------|-------|
| 1. Foundation | Complete | 2026-02-16 | uv, project structure, config, exceptions, app factory, Docker, 2 tests |
| 2. Database | Complete | 2026-02-17 | 12 Beanie documents, MongoDB/Weaviate connections, repository pattern, 68 tests |
| 3. LLM Provider | Complete | 2026-02-17 | ModelManager, circuit breaker, cost tracking callback, task-based routing, 77 tests |
| 4. Agent Architecture | Planned | — | |
| 5. Memory Systems | Planned | — | |
| 6. RAG Pipeline | Planned | — | |
| 7. API Layer | Planned | — | |
| 8. Guardrails | Planned | — | |
| 9. Evaluation | Planned | — | |
| 10. Deployment | Planned | — | |

### Module 2 Implementation Details

**Files created (21 total):**

| File | Purpose |
|------|---------|
| `src/db/base_document.py` | TimestampedDocument base class (created_at, updated_at, schema_version via Beanie event hooks) |
| `src/db/documents/enums.py` | StrEnum types: ApplicationStatus, DocumentType, MessageType, InterviewType, RemotePreference |
| `src/db/documents/embedded.py` | Shared embedded sub-model: SalaryRange (used by Profile and Job) |
| `src/db/documents/user.py` | User document (email unique index, hashed_password, is_active) |
| `src/db/documents/profile.py` | Profile document + UserPreferences embedded model |
| `src/db/documents/resume.py` | Resume document + ParsedResumeData, ContactInfo, WorkExperience, Education |
| `src/db/documents/job.py` | Job document + JobRequirements embedded model |
| `src/db/documents/company.py` | Company document (unique name index) |
| `src/db/documents/contact.py` | Contact document (LinkedIn POCs) |
| `src/db/documents/application.py` | Application document (pipeline tracking, compound indexes) |
| `src/db/documents/document_record.py` | AI-generated documents (cover letters, tailored resumes) |
| `src/db/documents/outreach_message.py` | Outreach message document |
| `src/db/documents/interview.py` | Interview document + InterviewNotes embedded model |
| `src/db/documents/star_story.py` | STAR story document (behavioral examples) |
| `src/db/documents/llm_usage.py` | LLM cost tracking document |
| `src/db/mongodb.py` | AsyncMongoClient + init_beanie connection lifecycle |
| `src/db/weaviate_client.py` | Weaviate v4 async client + 4 collection schemas |
| `src/repositories/base.py` | Generic BaseRepository[T] with CRUD + error handling |
| `src/repositories/user_repository.py` | UserRepository with auth-specific methods |
| `tests/unit/test_documents.py` | 52 document schema tests |
| `tests/unit/test_base_repository.py` | 16 repository tests with mocked Beanie |

**Files modified:**
- `src/db/documents/__init__.py` — ALL_DOCUMENT_MODELS registry (12 classes)
- `src/api/main.py` — Lifespan with actual DB connections
- `tests/conftest.py` — Mocked DB connections for test client
- `tests/unit/conftest.py` — Beanie _document_settings mock for unit tests

**Testing notes:**
- Beanie 2.0 requires init_beanie() before Document instantiation. Unit tests mock `_document_settings` to bypass this.
- Pydantic v2 strict `__setattr__` prevents setting mock methods on model instances. Repository tests use `patch.object(User, "method")` at class level instead.

**Reference documents:**
- `docs/DETAILED_PLAN.md` — Complete implementation plan with technical specs
- `CLAUDE.md` — Project context for future Claude sessions

### Module 3 Implementation Details

**Files created (6 total):**

| File | Purpose |
|------|---------|
| `src/llm/models.py` | TaskType (12 values), ProviderName, CircuitState enums; ModelConfig dataclass; ROUTING_TABLE mapping tasks to [primary, fallback] models; COST_PER_MILLION_TOKENS pricing table |
| `src/llm/circuit_breaker.py` | ProviderCircuit (CLOSED/OPEN/HALF_OPEN state machine, 3-failure threshold, 60s recovery); CircuitBreaker managing per-provider circuits |
| `src/llm/providers/__init__.py` | `detect_available_providers()` checks API key presence; `create_chat_model()` factory with lazy imports of ChatAnthropic/ChatOpenAI/ChatGroq |
| `src/llm/cost_tracker.py` | `calculate_cost()` pure function; token extraction for Anthropic and OpenAI response formats; `CostTrackingCallback(AsyncCallbackHandler)` that records LLMUsage documents on every LLM call |
| `src/llm/manager.py` | `ModelManager` with `get_model(task_type)` routing, circuit breaker integration, fallback chain; module-level lifecycle (`init_model_manager`/`close_model_manager`/`get_model_manager`) |
| `tests/unit/test_llm/` | 5 test files: test_models (15), test_circuit_breaker (15), test_cost_tracker (18), test_manager (15), test_providers (8) — 77 tests total |

**Files modified:**

- `src/llm/__init__.py` — Public API exports (TaskType, ProviderName, CostTrackingCallback, lifecycle functions)
- `src/api/main.py` — ModelManager init/close added to lifespan (after MongoDB, before yield)
- `tests/conftest.py` — Patches for `init_model_manager` and `close_model_manager` in test client fixture

**Key design decisions:**

- `get_model()` returns raw `BaseChatModel` — preserves LangGraph compatibility (`.bind_tools()`, `.with_structured_output()`)
- Cost tracking via LangChain `AsyncCallbackHandler` — works with any invocation pattern (invoke, stream, LangGraph)
- Circuit breaker is in-memory, per-provider — resets on server restart, which is fine for transient provider outages
- Budget enforcement deferred to Module 8 (Guardrails) — cost tracker only records, never blocks
- Provider instantiation gated by API key presence — missing keys are skipped, not errors

**Routing decisions:**

- Creative/analytical tasks (cover letters, research, interview prep) → Claude Sonnet
- Structured extraction (resume parsing, data extraction) → GPT-4o-mini
- Fast/cheap tasks (quick chat, general) → Claude Haiku
- All tasks have Groq Llama fallback (free tier, 500K tokens/day)

**Testing notes:**

- LangChain provider classes and LLMUsage are imported lazily (inside functions) to avoid circular dependencies. When patching lazy imports, you must patch at the source module (`langchain_anthropic.ChatAnthropic`) not the consuming module's namespace (`src.llm.providers.ChatAnthropic`).

### Module 4 Implementation Details

**Files created (7 source + 4 test files):**

| File | Purpose |
|------|---------|
| `src/agents/base.py` | `BaseAgent` abstract class — `__call__` makes agents directly usable as LangGraph nodes. Handles model selection, system prompt injection, cost tracking callbacks, and circuit breaker recording. Subclasses implement `build_messages(state)` and `process_response(response, state)`. |
| `src/agents/cover_letter.py` | `RequirementsAnalyst` (TaskType.DATA_EXTRACTION, GPT-4o-mini, temp=0.0) extracts structured requirements from JDs. `CoverLetterWriter` (TaskType.COVER_LETTER, Claude Sonnet, temp=0.7) generates tailored cover letters with revision loop support. |
| `src/workflows/checkpointer.py` | MongoDBSaver lifecycle with dedicated sync `MongoClient` (separate from Beanie's async client). Module-level `init_checkpointer`/`close_checkpointer`/`get_checkpointer` matching established patterns. |
| `src/workflows/states/cover_letter.py` | `CoverLetterState(TypedDict)` with `Annotated[list, add_messages]` for append-only message history. Tracks job_description, resume_text, requirements_analysis, cover_letter, feedback, and status. |
| `src/workflows/graphs/cover_letter.py` | Complete LangGraph workflow: `analyze_requirements` -> `write_cover_letter` -> `human_review` with HITL interrupt/resume and revision loop via `Command`. |
| `tests/unit/test_agents/` | `test_base.py` (17 tests: init, `__call__` lifecycle, cost tracking, circuit breaker, error handling, user_id extraction); `test_cover_letter.py` (13 tests: agent config, message building, revision handling, response extraction) |
| `tests/unit/test_workflows/` | `test_checkpointer.py` (5 tests: lifecycle pattern); `test_cover_letter_graph.py` (6 tests: graph structure, HITL interrupt, approve flow, revision loop, revision-then-approve) |

**Files modified:**

- `src/api/main.py` — Added `init_checkpointer`/`close_checkpointer` to lifespan (startup step 4, shutdown step 1)
- `tests/conftest.py` — Added patches for checkpointer in test client fixture
- `src/agents/__init__.py` — Public exports: BaseAgent, RequirementsAnalyst, CoverLetterWriter
- `src/workflows/__init__.py` — Public exports: checkpointer lifecycle functions
- `src/workflows/states/__init__.py` — Exports CoverLetterState
- `src/workflows/graphs/__init__.py` — Exports build_cover_letter_graph

**Key design decisions:**

- `BaseAgent.__call__` as LangGraph node interface — agents plug directly into `builder.add_node("name", agent_instance)` without adapter functions
- `user_id` from `config["configurable"]["user_id"]` (not state) — follows LangGraph convention for session metadata; avoids coupling BaseAgent to specific state schemas
- Separate sync MongoClient for MongoDBSaver — Beanie uses `AsyncMongoClient`; MongoDBSaver requires synchronous `pymongo.MongoClient` internally; lightweight separate connection pool
- `interrupt(value)` for HITL (not `interrupt_before`) — modern LangGraph pattern that lets the node prepare a review payload and handle the resume response in one place
- `Command(update=..., goto=...)` for routing after review — explicit control over state updates and next node; cleaner than conditional edges for HITL flows
- Node functions typed with `RunnableConfig` (not `dict`) — required for LangGraph to inject the config parameter into node functions

**Testing notes:**

- Graph tests use `MemorySaver` (in-memory checkpointer) — no MongoDB needed for unit tests
- Agent LLM calls mocked at `get_model_manager()` level in agent tests, at `_analyst`/`_writer` singleton level in graph tests — separates agent behavior testing from graph behavior testing
- `interrupt()` in graph tests verified via `graph.aget_state(config).tasks[0].interrupts[0].value` — confirms the interrupt payload contains the cover letter draft

### Module 5 Implementation Details

**Files created (10 source + 7 test files):**

| File | Purpose |
|------|---------|
| `src/rag/embeddings.py` | BGE-small-en-v1.5 embedding service lifecycle. Module-level `init_embeddings`/`close_embeddings`/`get_embedding_service` matching established patterns. `embed_texts()` and `embed_query()` async wrappers via `asyncio.to_thread()` to avoid blocking the event loop. |
| `src/rag/retriever.py` | Weaviate search bridge — thin async functions that embed a query then delegate to WeaviateRepository. `hybrid_search()` (BM25 + vector) and `semantic_search()` (pure vector). |
| `src/repositories/weaviate_base.py` | `WeaviateRepository` — generic base for all Weaviate collections, parallel to `BaseRepository[T]` for MongoDB. Provides `ensure_tenant`, `insert_object`, `search_by_vector`, `hybrid_search`, `delete_object`. Wraps errors in `VectorSearchError`. |
| `src/repositories/resume_chunk_repository.py` | `ResumeChunkRepository(WeaviateRepository)` — `search_by_job_description()` for finding resume sections matching a JD. |
| `src/repositories/cover_letter_embedding_repository.py` | `CoverLetterEmbeddingRepository(WeaviateRepository)` — `search_similar_letters()` for finding past cover letters for similar roles. |
| `src/repositories/star_story_embedding_repository.py` | `STARStoryEmbeddingRepository(WeaviateRepository)` — `search_by_question()` for matching STAR stories to interview questions. |
| `src/memory/types.py` | `MemoryItem` and `MemoryContext` dataclasses — data transfer objects for the memory pipeline. |
| `src/memory/recipes.py` | `MemoryRecipe` frozen dataclass + `MEMORY_RECIPES` config table keyed by agent name. Declares per-agent relevance/recency weights, collection targets, and hybrid alpha. |
| `src/memory/retrieval.py` | `retrieve_memories()` orchestrator — looks up recipe, searches Weaviate collections, scores/merges results, returns formatted `MemoryContext`. Graceful degradation on failures. |
| `src/memory/summarizer.py` | `summarize_messages()` — threshold-based LLM summarization using TaskType.GENERAL. Splits messages into old (summarized) and recent (preserved). `summarize_if_needed()` graph node wrapper. |
| `tests/unit/test_rag/` | `test_embeddings.py` (16 tests: lifecycle, async wrappers, error handling); `test_retriever.py` (5 tests: hybrid/semantic search wiring) |
| `tests/unit/test_repositories/` | `test_weaviate_base.py` (15 tests: tenant management, CRUD, search, error wrapping) |
| `tests/unit/test_memory/` | `test_recipes.py` (11 tests: structure validation, weight ranges, collection references); `test_retrieval.py` (16 tests: orchestration, scoring, formatting, helpers); `test_summarizer.py` (11 tests: threshold, split strategy, graph node) |

**Files modified:**

- `src/core/config.py` — Added `EmbeddingSettings` sub-model (model_name, dimensions, cache_dir) and `embedding` field on root `Settings`
- `src/core/exceptions.py` — Added `VectorSearchError` (500, VECTOR_SEARCH_ERROR) and `EmbeddingError` (500, EMBEDDING_ERROR)
- `src/api/main.py` — Added `init_embeddings`/`close_embeddings` to lifespan (startup step 3 after Weaviate, shutdown step 3 before Weaviate)
- `tests/conftest.py` — Added patches for `init_embeddings`/`close_embeddings` in test client fixture
- `src/workflows/states/cover_letter.py` — Added `memory_context: str` field to `CoverLetterState`
- `src/workflows/graphs/cover_letter.py` — Added `retrieve_memories` node between `analyze_requirements` and `write_cover_letter`; graceful degradation if memory retrieval fails
- `src/agents/cover_letter.py` — Updated `CoverLetterWriter.build_messages()` to include `state["memory_context"]` when present

**Key design decisions:**

- Embedding service as module-level lifecycle — BGE-small-en-v1.5 (~130MB) loads once at startup, matching the init/close/get pattern used by MongoDB, Weaviate, ModelManager, and Checkpointer
- `asyncio.to_thread()` for CPU-bound embedding — prevents blocking the async event loop during matrix multiplication
- `WeaviateRepository` parallel to `BaseRepository[T]` — identical CRUD patterns across 4 collections, same error wrapping strategy (VectorSearchError vs DatabaseError)
- Per-agent memory recipes as declarative config table (`MEMORY_RECIPES`) — same pattern as `ROUTING_TABLE` in models.py; centralized and tunable without touching agent code
- Memory injection via state field (`memory_context`), not BaseAgent changes — keeps agents stateless and testable; a `retrieve_memories` graph node populates the field before the writing agent runs
- `normalize_embeddings=True` — BGE models use cosine similarity; pre-normalizing to unit vectors means cosine = dot product, faster computation in Weaviate's HNSW index
- Graceful degradation everywhere — memory retrieval failures return empty context (not crash the workflow); new users without tenants get empty results silently

**Testing notes:**

- Embedding service tests use `autouse` fixture to reset module-level `_embeddings` between tests
- Weaviate tests mock the full collection chain: `client.collections.get() -> collection.with_tenant() -> multi_collection`
- Recipe tests validate against `WEAVIATE_COLLECTIONS` from `weaviate_client.py` to ensure collection references are valid
- Memory retrieval tests mock at the `hybrid_search` bridge level, not the Weaviate client level — isolates orchestration logic from search internals
- Graph tests (from Module 4) continue to pass with the new `retrieve_memories` node — existing mocks at agent level skip memory retrieval automatically

### Module 6 Implementation Details

**Files created (2 source + 2 test files):**

| File | Purpose |
|------|---------|
| `src/rag/chunker.py` | Document-aware chunking for resumes (12 section heading patterns) and job descriptions (8 heading patterns), plus fixed-size fallback (500 tokens, 50 overlap). `Chunk` frozen dataclass as intermediate representation. `chunk_resume()`, `chunk_job_description()`, `chunk_fixed_size()` public functions. |
| `src/services/indexing_service.py` | `IndexingService` — RAG write-path orchestrator. Constructor-injected with 8 repositories (4 MongoDB + 4 Weaviate). `index_resume()`, `index_job()`, `index_cover_letter()`, `index_star_story()` methods follow the pattern: fetch from MongoDB, delete old chunks, chunk, embed, store in Weaviate. `delete_index()` for generic cleanup. |
| `tests/unit/test_rag/test_chunker.py` | 27 tests: Chunk dataclass (frozen, fields, defaults), resume chunking (section splitting, metadata, preamble, fallback), JD chunking (headings, formats), fixed-size chunking (overlap, custom params), internal helper |
| `tests/unit/test_services/test_indexing_service.py` | 37 tests: index_resume (8), index_job (6), index_cover_letter (6), index_star_story (6), delete_index (4), internal helpers (7). All repositories mocked via constructor injection. |

**Files modified:**

- `src/repositories/weaviate_base.py` — Added `search_by_property()` method using Weaviate v4 `Filter.by_property().equal()` API. Used by IndexingService for delete-before-reindex (find existing chunks by resume_id/job_id, then delete each). 3 new tests added to existing test file.
- `src/services/__init__.py` — Updated comment listing IndexingService as available service

**Key design decisions:**

- Document-aware chunking with regex section splitting — resumes and JDs have predictable section headings; regex is fast, deterministic, and free (no LLM calls needed)
- Fixed-size fallback (500 tokens, 50 overlap) for text without recognized headings — ensures every document can be indexed regardless of structure
- `Chunk` as frozen dataclass — immutable data flowing through the pipeline, matching the `MemoryRecipe` pattern from Module 5
- Constructor-injected IndexingService — 8 repositories injected at creation time, fully testable with mocks, no global state or patching required
- Delete-before-reindex for idempotency — old chunks removed before new ones stored; handles structural changes correctly (e.g., resume gains a new section)
- Cover letter indexing takes company/role as parameters — DocumentRecord doesn't store these directly; the calling workflow (which already has Job context) passes them in
- No API endpoints yet — IndexingService is a backend service that will be called by Profile Setup and Job Discovery workflows in future modules

**Testing notes:**

- Chunker tests are synchronous (pure logic, no async I/O) — no mocking needed
- IndexingService tests mock at the repository level via constructor injection — no module-level patching needed except for `embed_texts`
- Weaviate `search_by_property` tests extend the existing fixture (added `fetch_objects` mock to the collection chain)
- 67 new tests total (27 chunker + 37 indexing + 3 weaviate repo), bringing project total to 327

---

*Last updated: 2026-02-17*
