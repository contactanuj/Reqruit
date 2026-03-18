# Architecture Reference

> Technical deep-dive into Reqruit's system design. Intended for contributors and anyone studying the codebase.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Startup Sequence](#2-startup-sequence)
3. [Request Lifecycle](#3-request-lifecycle)
4. [Authentication Flow](#4-authentication-flow)
5. [Repository Pattern](#5-repository-pattern)
6. [LLM Provider Layer](#6-llm-provider-layer)
7. [LangGraph Workflow Engine](#7-langgraph-workflow-engine)
8. [Cover Letter HITL Flow](#8-cover-letter-hitl-flow)
9. [RAG Pipeline](#9-rag-pipeline)
10. [Memory System](#10-memory-system)
11. [Guardrails](#11-guardrails)
12. [Error Handling](#12-error-handling)
13. [Observability](#13-observability)
14. [Configuration System](#14-configuration-system)
15. [Testing Architecture](#15-testing-architecture)

---

## 1. System Overview

Reqruit is structured in 7 vertical layers. Each layer has a single responsibility and communicates only with adjacent layers.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 7: API (FastAPI routes, middleware, dependencies)     │
│  Entry point: src/api/main.py → create_app()                │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: Services (business logic orchestration)           │
│  IndexingService, MetricsService                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Agents + Workflows (LangGraph state machines)     │
│  13 agents, 4 workflows, HITL interrupt/resume              │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: LLM Provider (routing, circuit breaker, cost)     │
│  ModelManager → Anthropic | OpenAI | Groq                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: RAG + Memory (embeddings, retrieval, chunking)    │
│  BGE-small-en-v1.5, Weaviate hybrid search, MemoryRecipes   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Repositories (data access, owner-scoping)         │
│  BaseRepository[T] + WeaviateRepository                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Databases (MongoDB + Weaviate)                    │
│  12 Beanie documents + 4 vector collections                 │
└─────────────────────────────────────────────────────────────┘
```

**Key invariants:**
- Routes never query the DB directly — always through a repository
- Services never import from `src/api/` — no HTTP concepts below Layer 6
- All I/O is `async/await` — no blocking calls anywhere
- Every resource access verifies `user_id` ownership before returning data
- Thread-level ownership enforced: SSE stream and review endpoints validate `thread_id` belongs to the requesting user's `DocumentRecord`, not just that `application_id` is owned

---

## 2. Startup Sequence

FastAPI's lifespan context manager controls startup and shutdown. Order matters:

```python
# src/api/main.py → lifespan()
async def lifespan(_app: FastAPI):
    # -- STARTUP --
    await connect_mongodb(settings)      # 1. Beanie registers all 12 documents
    await connect_weaviate(settings)     # 2. Weaviate collections verified/created
    init_embeddings(settings)            # 3. BGE model loads (~130MB, 2-3s)
    init_model_manager(settings)         # 4. Detects available LLM providers
    init_checkpointer(settings)          # 5. MongoDBSaver for LangGraph checkpoints
    init_cover_letter_graph(            # 6. Compile graph once, reuse per request
        get_checkpointer()
    )
    yield
    # -- SHUTDOWN (reverse order) --
    close_checkpointer()
    close_model_manager()
    close_embeddings()
    await close_weaviate()
    close_mongodb()
```

**Why this order:**
- MongoDB first: Beanie needs to register document models before anything else inserts/queries
- Weaviate second: collections must exist before embedding inserts can target them
- Embeddings third: loaded after Weaviate because embeddings feed into Weaviate
- ModelManager fourth: detects API keys; cost callback uses Beanie (`LLMUsage.insert()`)
- Checkpointer fifth: needs the MongoDB connection to already be alive
- Graph sixth: compilation requires the checkpointer

---

## 3. Request Lifecycle

A typical authenticated request flows through 5 layers:

```
HTTP Request
     │
     ▼
RequestLoggingMiddleware        → binds request_id + user_id to structlog context
     │
     ▼
CORSMiddleware                  → adds CORS headers (permissive in dev)
     │
     ▼
Route Handler (FastAPI)         → validates Pydantic schemas, calls Depends()
     │
     ├── get_current_user()     → decode JWT, look up User in MongoDB
     ├── get_*_repository()     → create repository instance
     │
     ▼
Repository Method               → queries MongoDB with owner-scope filter
     │
     ▼
Domain Logic                    → business rules, state machine checks
     │
     ▼
JSON Response / StreamingResponse
```

**Middleware stack order (bottom to top, meaning outer to inner for requests):**
1. `RequestLoggingMiddleware` — outermost, runs first on request
2. `CORSMiddleware` — CORS headers before logging so they're always present

```python
# Order in create_app():
application.add_middleware(CORSMiddleware, ...)        # added first = outer
application.add_middleware(RequestLoggingMiddleware)   # added second = inner
# FastAPI wraps in reverse, so CORS is the outermost handler
```

---

## 4. Authentication Flow

### Token Architecture

```
Login → { access_token (15min), refresh_token (7d) }

access_token payload:  { sub: user_id, type: "access",  exp: ... }
refresh_token payload: { sub: user_id, type: "refresh", exp: ... }
```

### Access Flow

```
Request with Bearer token
     │
     ▼
HTTPBearer()                    → extracts token from Authorization header
                                   returns 401 if header is missing
     │
     ▼
jwt.decode()                    → verifies signature + expiry
                                   raises 401 on ExpiredSignatureError
     │
     ▼
payload.get("type") == "access" → guards against using refresh tokens as access
                                   raises 401 if wrong type
     │
     ▼
User.get(PydanticObjectId(sub)) → one MongoDB lookup per request
                                   raises 401 if user doesn't exist or inactive
     │
     ▼
Endpoint receives: User object
```

### Token Refresh Flow (Server-Side Rotation with CAS)

```
POST /auth/refresh { "refresh_token": "..." }
     │
     ▼
Decode JWT → extract jti, family_id, sub
     │
     ▼
Atomic CAS revoke: find_one_and_update({token_jti, is_revoked: false} → {is_revoked: true})
     │
     ├─ CAS success (first use) ──────────────────────────┐
     │                                                     ▼
     │                                          Issue new access_token + refresh_token
     │                                          (same family_id, new jti)
     │                                          Store new RefreshToken in DB
     │
     └─ CAS failure (already revoked = REUSE!) ──────────┐
                                                          ▼
                                               Revoke ALL tokens in family
                                               Return 401 (theft detected)
```

Key properties:

- **Atomic CAS**: PyMongo `find_one_and_update` ensures only one concurrent request wins
- **Family tracking**: All rotated tokens share a `family_id`; reuse triggers full family revocation
- **Backward compat**: Old tokens without `jti`/`family_id` claims return 401

### Why PyJWT, not python-jose

`python-jose` has been unmaintained since 2021 with known vulnerabilities. PyJWT is actively maintained, simpler API, sufficient for HS256 symmetric tokens in a single-service app. RS256 (asymmetric) would be needed only if multiple independent services need to verify tokens.

---

## 5. Repository Pattern

All data access goes through repositories. No Beanie/Weaviate queries outside `src/repositories/`.

### MongoDB: BaseRepository[T]

```python
class BaseRepository(Generic[T]):
    _model: type[T]                          # Beanie document class

    async def create(doc: T) -> T
    async def get_by_id(id: PydanticObjectId) -> T | None
    async def find_many(filter: dict, ...) -> list[T]
    async def find_by_ids(ids: list[PydanticObjectId]) -> list[T]   # batch IN query
    async def update(id: PydanticObjectId, data: dict) -> T | None
    async def delete(id: PydanticObjectId) -> bool
```

**Owner-scoping convention:** Every collection-specific repo adds query methods that always include `user_id` in the filter. Example:

```python
class ApplicationRepository(BaseRepository[Application]):
    async def get_by_user_and_id(user_id, application_id) -> Application | None:
        return await Application.find_one({
            "_id": application_id,
            "user_id": user_id       # owner-scope enforced here, not in route
        })
```

**N+1 prevention:** The `find_by_ids()` method issues a single `$in` query instead of per-document lookups:

```python
# get_kanban / list_applications pattern
applications = await app_repo.get_kanban(user_id)          # query 1
job_ids = [app.job_id for app in applications]
jobs = await job_repo.find_by_ids(job_ids)                 # query 2 (single IN)
job_map = {str(j.id): j for j in jobs}                    # O(1) lookup in route
```

### Weaviate: WeaviateRepository

```python
class WeaviateRepository:
    _collection_name: str

    async def ensure_tenant(tenant: str) -> None          # multi-tenancy setup
    async def insert_object(properties, vector, tenant) -> str
    async def search_by_vector(vector, tenant, limit) -> list[dict]
    async def hybrid_search(query, vector, tenant, ...) -> list[dict]
    async def search_by_property(property_name, value, tenant) -> list[dict]
    async def delete_object(uuid, tenant) -> None
```

**Multi-tenancy:** Each user's data is isolated in a Weaviate tenant (tenant ID = `user_id`). This enables per-user data isolation without running separate Weaviate instances.

---

## 6. LLM Provider Layer

### Routing Table

Tasks map to an ordered list of `(provider, model, max_tokens, temperature)` configs. The manager walks the list and returns the first available provider:

```
TaskType.COVER_LETTER    → [Claude Sonnet, GPT-4o, Groq Llama70B]
TaskType.DATA_EXTRACTION → [GPT-4o-mini, Claude Haiku, Groq Llama8B]
TaskType.QUICK_CHAT      → [Groq Llama70B, Claude Haiku]
TaskType.SELF_CHECK      → [Groq Llama70B]    # free-only for guardrail checks
```

### Provider Selection Logic

```python
def get_model(task_type: TaskType) -> BaseChatModel:
    for config in ROUTING_TABLE[task_type]:
        if config.provider not in self._available_providers:
            continue   # no API key configured
        if not self._circuit_breaker.is_available(config.provider):
            continue   # circuit is open (recent failures)
        return self._create_model(config)
    raise LLMProviderError("All providers unavailable")
```

### Circuit Breaker States

```
CLOSED ──(5 failures in 60s)──► OPEN ──(30s cooldown)──► HALF_OPEN
  ▲                                                            │
  └──────────────────(1 success)──────────────────────────────┘
```

- **CLOSED**: normal operation, requests go through
- **OPEN**: provider is failing, requests are blocked immediately (no wasted API calls)
- **HALF_OPEN**: one test request allowed; success → CLOSED, failure → OPEN

### Cost Tracking

Every LLM call goes through `CostTrackingCallback`, a LangChain `BaseCallbackHandler`:

```python
callback = manager.create_cost_callback(
    user_id="...", agent="cover_letter_writer", task_type="cover_letter"
)
result = await model.ainvoke(messages, config={"callbacks": [callback]})
# callback.on_llm_end() fires → inserts LLMUsage record to MongoDB
```

`LLMUsage` stores: `user_id`, `agent`, `model`, `provider`, `input_tokens`, `output_tokens`, `cost_usd`, `timestamp`. This feeds the `/track/usage` analytics endpoint.

---

## 7. LangGraph Workflow Engine

### State Pattern

Every workflow uses a `TypedDict` state — a plain dict with typed keys. LangGraph merges node return values into state automatically.

```python
class CoverLetterState(TypedDict):
    job_description: str
    resume_text: str
    requirements_analysis: str     # set by analyze_requirements node
    memory_context: str            # set by retrieve_memories node
    cover_letter: str              # set by write_cover_letter node
    feedback: str                  # set on revision
    status: str                    # "analyzing" | "writing" | "approved" | ...
```

### Graph Structure: Cover Letter Workflow

```
START
  │
  ▼
analyze_requirements     ← RequirementsAnalyst agent
  │                        reads job_description → writes requirements_analysis
  ▼
retrieve_memories        ← fetches resume chunks + past letters from Weaviate
  │                        gracefully degrades if no tenant or empty corpus
  ▼
write_cover_letter       ← CoverLetterWriter agent
  │                        reads requirements_analysis + memory_context + feedback
  │                        writes cover_letter
  ▼
human_review             ← calls interrupt() → pauses graph execution
  │                        checkpoint saved to MongoDB
  │
  ├── "approve" → status="approved" → END
  │
  └── "revise"  → feedback stored → back to write_cover_letter
```

### Checkpoint Lifecycle

```
1. POST /cover-letter
   → thread_id = uuid4()
   → DocumentRecord created with thread_id

2. GET /cover-letter/stream?thread_id=X  (with reconnect detection)
   → endpoint calls graph.aget_state(config) to check checkpoint state
   → if no checkpoint (empty values): fresh start with initial_state
   → if at human_review interrupt: emits awaiting_review from saved state (no re-run)
   → if in-flight at another node: graph.astream(None, config) resumes from checkpoint
   → if graph completed (values populated, next empty): emits completed event
   → fresh start: graph.astream(initial_state, config) runs from beginning
   → graph runs nodes, checkpointing after each
   → hits interrupt() → yields awaiting_review SSE event → stream closes
   → checkpoint in MongoDB: complete state at interrupt point

3. POST /cover-letter/review {"action": "revise", "feedback": "..."}
   → graph.ainvoke(Command(resume={"action": "revise"}), config)
   → graph loads checkpoint for thread_id X
   → resumes from human_review node
   → routes to write_cover_letter with feedback in state
   → hits interrupt() again → new checkpoint

4. POST /cover-letter/review {"action": "approve"}
   → graph loads checkpoint → resumes → status="approved" → END
   → DocumentRecord.content saved, is_approved=True
```

### Singleton Pattern

The compiled graph is built once at startup (stateless after compilation):

```python
# src/workflows/graphs/cover_letter.py
_compiled_graph: CompiledStateGraph | None = None

def init_cover_letter_graph(checkpointer):
    global _compiled_graph
    _compiled_graph = build_cover_letter_graph(checkpointer)

def get_cover_letter_graph() -> CompiledStateGraph:
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized")
    return _compiled_graph
```

State is NOT in the graph object — it lives in the checkpointer (MongoDB). The compiled graph is safe to reuse across concurrent requests.

---

## 8. Cover Letter HITL Flow

End-to-end sequence diagram:

```
Client              FastAPI            LangGraph          MongoDB
  │                    │                   │                  │
  │─POST /cover-letter─►│                  │                  │
  │                    │──────────────────────────────────────►│
  │                    │  DocumentRecord.insert(thread_id)     │
  │◄──202 {thread_id}──│                   │                  │
  │                    │                   │                  │
  │─GET /stream?tid=X──►│                  │                  │
  │                    │─astream(state, config={thread_id: X})─►│
  │                    │                   │─checkpoint─────────►│
  │◄─node_complete─────│◄──analyze_done────│                  │
  │◄─node_complete─────│◄──memories_done───│                  │
  │◄─node_complete─────│◄──letter_done─────│                  │
  │                    │                   │─interrupt()───────►│ (checkpoint)
  │◄─awaiting_review───│◄──__interrupt__───│                  │
  │  {cover_letter}    │                   │                  │
  │                    │                   │                  │
  │──POST /review──────►│                  │                  │
  │  {action: approve} │                   │                  │
  │                    │─ainvoke(Command(resume={approve}))────►│ (load checkpoint)
  │                    │                   │──────status=approved──►END
  │                    │──────────────────────────────────────►│
  │                    │  DocumentRecord.update(content, approved=True)
  │◄──{status:approved}│                   │                  │
```

---

## 9. RAG Pipeline

### Write Path (Indexing)

```
Source Document (MongoDB)
     │
     ▼
IndexingService.index_resume(resume_id, user_id)
     │
     ├── fetch Resume from MongoDB
     ├── _delete_existing(resume_id, weaviate_repo)   ← idempotent
     ├── ensure_tenant(user_id)
     ├── chunk_resume(raw_text, resume_id, user_id)   ← document-aware chunking
     │     ├── split by RESUME_SECTIONS regex (12 heading patterns)
     │     └── fallback: chunk_fixed_size(500 tokens, 50 overlap)
     ├── embed_texts([chunk.content for chunk in chunks])  ← BGE-small batch
     └── insert_object(properties, vector, tenant) for each chunk
```

**Delete-before-reindex:** When a resume is re-uploaded, old chunks are found via `search_by_property("resume_id", resume_id)` and deleted before new ones are inserted. Avoids stale chunk accumulation and is simpler than upsert-by-content-hash.

### Read Path (Retrieval)

```
Agent needs context (e.g., CoverLetterWriter)
     │
     ▼
retrieve_memories(agent_name="cover_letter_writer", query, user_id)
     │
     ├── load MemoryRecipe for "cover_letter_writer"
     │     recipe = {
     │       weaviate_collections: ["ResumeChunk", "CoverLetterEmbedding"],
     │       recency_collections: [],
     │       relevance_weight: 0.7,
     │       recency_weight: 0.3,
     │     }
     │
     ├── embed_query(query)   ← single BGE embedding
     │
     ├── for each collection in recipe:
     │     hybrid_search(query, vector, tenant=user_id, limit=5)
     │     ← Weaviate BM25 + vector combined score
     │
     └── merge + format → MemoryContext.formatted (string for LLM prompt)
```

### Chunking Strategy

| Input Type | Strategy | Chunk Type | Max Size |
|-----------|---------|-----------|---------|
| Resume | Split by section headings (12 regex patterns) | heading-derived | whole section |
| Job Description | Split by JD headings (8 regex patterns) | heading-derived | whole section |
| Any text (fallback) | Fixed-size sliding window | "fixed_size" | 500 tokens |
| Cover letter | Single embedding (no chunking) | "full_text" | whole document |
| STAR story | Concatenate all 4 fields, single embedding | "full_text" | whole story |

**Section heading patterns (resume):** work_experience, education, skills, summary, objective, projects, certifications, awards, publications, volunteer, languages, references.

**Section heading patterns (JD):** about, responsibilities, requirements, qualifications, benefits, how_to_apply, about_the_team, what_youll_do.

---

## 10. Memory System

### Architecture

Each agent has a `MemoryRecipe` that configures its retrieval behavior:

```python
@dataclass(frozen=True)
class MemoryRecipe:
    weaviate_collections: list[str]      # which vector collections to search
    recency_collections: list[str]       # which MongoDB collections for recent items
    relevance_weight: float              # weight for semantic similarity
    recency_weight: float                # weight for recency scoring
    max_items: int                       # total items to include in context
```

### Retrieval Flow

```
retrieve_memories(agent_name, query, user_id)
     │
     ├── 1. Semantic retrieval (Weaviate)
     │      embed_query(query) → vector
     │      for each weaviate_collection:
     │          hybrid_search(query, vector, tenant=user_id)
     │
     ├── 2. Recency retrieval (MongoDB)
     │      for each recency_collection:
     │          find_many({"user_id": user_id}, sort={"created_at": -1})
     │
     ├── 3. Merge and score
     │      score = relevance_weight * semantic_score
     │            + recency_weight * recency_score
     │      sort by score, take top max_items
     │
     └── 4. Format
            MemoryContext(items=[...], formatted="...\n\n...")
            formatted = string ready to inject into LLM prompt
```

### Summarization

When message history grows long, `MemorySummarizer` compresses old messages:

```
messages[0..N-5]  →  LLM summarize  →  single "summary" message
messages[N-5..N]  →  kept verbatim
```

Uses the cheapest available model (Groq Llama) for cost efficiency.

---

## 11. Guardrails

### Input Validation (3 layers)

```
User input (free text)
     │
     ▼
Layer 1: Pydantic schema          → type coercion, length limits, field presence
     │
     ▼
Layer 2: Rule-based checks        → profanity, SQL injection patterns, PII in
     │                              unexpected fields (e.g., injected emails in
     │                              job titles)
     ▼
Layer 3: LLM moderation           → OpenAI Moderation API (free, synchronous)
     │                              + Llama Guard via Groq (free-text only,
     │                                asynchronous, for extra coverage)
     │
     ▼
Pass or raise BusinessValidationError("CONTENT_POLICY_VIOLATION")
```

### Output Validation (3 layers)

```
LLM raw output
     │
     ▼
Layer 1: Schema enforcement       → Pydantic parse, required fields present
     │
     ▼
Layer 2: Content rules            → length bounds, forbidden patterns,
     │                              PII not leaked in outputs
     ▼
Layer 3: Self-check (critical)    → Groq Llama self-reviews the output:
                                    "Does this cover letter contain fabrications?"
                                    Only for high-stakes outputs (cover letters,
                                    tailored resumes) — not every LLM call.
```

### PII Detection

`pii_detector.py` uses compiled regex patterns for 10+ PII types:

```
SSN:   \b\d{3}-\d{2}-\d{4}\b
Email: [standard RFC 5322 pattern]
Phone: various US formats
CC:    Luhn-validated card numbers
...
```

Returns `list[PIIMatch]` with type, value, and character offset. Used by input guardrails to block PII submission in unexpected fields, and by output guardrails to ensure PII isn't leaked in AI-generated content.

---

## 12. Error Handling

### Exception Hierarchy

```
Exception
  └── AppError (status_code, detail, error_code)
        ├── AuthenticationError    → 401  AUTH_TOKEN_EXPIRED, AUTH_TOKEN_INVALID...
        ├── AuthorizationError     → 403  FORBIDDEN
        ├── NotFoundError          → 404  {RESOURCE}_NOT_FOUND
        ├── ConflictError          → 409  CONFLICT, EMAIL_ALREADY_REGISTERED
        ├── BusinessValidationError → 422  INVALID_STATUS_TRANSITION, INVALID_ACTION...
        ├── RateLimitError         → 429  RATE_LIMITED
        ├── LLMProviderError       → 502  LLM_PROVIDER_ERROR, LLM_ALL_UNAVAILABLE
        ├── DatabaseError          → 500  DATABASE_ERROR
        ├── VectorSearchError      → 500  VECTOR_SEARCH_ERROR
        └── EmbeddingError         → 500  EMBEDDING_ERROR
```

### Exception Handler (registered in `create_app()`)

```python
@app.exception_handler(AppError)
async def app_exception_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,   # machine-readable
            "detail":     exc.detail,       # human-readable
        }
    )
```

FastAPI's built-in `RequestValidationError` (422 for bad schemas) and `HTTPException` handlers remain active. The custom handler only intercepts `AppError` subclasses.

### Error Code Convention

All error codes follow `UPPER_SNAKE_CASE`. Prefixes:
- `AUTH_` — authentication/authorization failures
- `{RESOURCE}_NOT_FOUND` — auto-generated by `NotFoundError(resource_type)`
- `INVALID_STATUS_TRANSITION` — state machine violations
- `LLM_` — LLM provider failures
- `VECTOR_SEARCH_ERROR`, `EMBEDDING_ERROR`, `DATABASE_ERROR` — infrastructure

---

## 13. Observability

### Structured Logging (structlog)

Every log entry is a JSON object in production, colored key=value in development:

```python
logger.info(
    "application_status_updated",
    user_id=str(current_user.id),
    application_id=application_id,
    old_status=old_status,
    new_status=new_status,
)
```

Request-scoped context (request_id, user_id) is automatically included in all log calls via `structlog.contextvars`:

```python
# In RequestLoggingMiddleware — runs once per request
structlog.contextvars.bind_contextvars(
    request_id=str(uuid4()),
    user_id=user_id,
)
# Every subsequent logger.info() in this coroutine includes request_id and user_id
```

### LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true`, every LangChain/LangGraph call is traced automatically. Traces include: inputs, outputs, token counts, latency per node, and intermediate steps. Used for:
- Debugging prompt failures
- Building evaluation datasets
- Comparing model outputs

### Metrics (MetricsService)

`src/services/metrics_service.py` queries the `llm_usage` collection for:
- Total tokens/cost per user per period
- Cost breakdown by agent and model
- Daily active users
- Application funnel (saved → applied → interviewing → offered)

---

## 14. Configuration System

### Settings Hierarchy

```python
Settings (root, reads .env file)
  ├── app:        AppSettings       (APP_* env vars)
  ├── mongodb:    MongoDBSettings   (MONGODB_* env vars)
  ├── weaviate:   WeaviateSettings  (WEAVIATE_* env vars)
  ├── auth:       AuthSettings      (JWT_*, ACCESS_TOKEN_*, REFRESH_TOKEN_*)
  ├── anthropic:  AnthropicSettings (ANTHROPIC_*)
  ├── openai:     OpenAISettings    (OPENAI_*)
  ├── groq:       GroqSettings      (GROQ_*)
  ├── embedding:  EmbeddingSettings (EMBEDDING_*)
  └── langsmith:  LangSmithSettings (LANGCHAIN_*)
```

### Singleton with Cache Clear

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

# In tests:
get_settings.cache_clear()
os.environ["APP_ENV"] = "testing"
settings = get_settings()   # reads fresh with test env vars
```

**Critical bug avoidance:** Sub-settings must use `Field(default_factory=SubClass)`, NOT `SubClass()` as a default. The latter evaluates at class definition time, making cache_clear() ineffective because the sub-settings are already instantiated.

---

## 15. Testing Architecture

### Test Pyramid

```
                   /\
                  /  \
                 / E2E \    (not implemented — integration tests cover this)
                /──────\
               /        \
              / Integration\  tests/integration/ — real LLM + DB calls
             /──────────────\
            /                \
           /   Unit Tests (494) \  tests/unit/ — mocked deps, fast, CI
          /──────────────────────\
```

### Unit Test Patterns

**Repository tests:** Mock `beanie.Document` methods with `AsyncMock`. Never hit real MongoDB.

**Route tests:** Use `httpx.AsyncClient` with the FastAPI test app + `dependency_overrides`:

```python
@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    mock_user = MagicMock(spec=User)
    mock_user.id = PydanticObjectId()
    client.app.dependency_overrides[get_current_user] = lambda: mock_user
    return client
```

**LangGraph graph tests:** Inject `MemorySaver` checkpointer instead of `MongoDBSaver`:

```python
from langgraph.checkpoint.memory import MemorySaver
graph = build_cover_letter_graph(MemorySaver())
```

**Async test configuration:** `pytest.ini` / `pyproject.toml` sets `asyncio_mode = "auto"` — all async test functions run without `@pytest.mark.asyncio`.

### Fixture Hierarchy

```
conftest.py (root)
  ├── settings()           → fresh Settings with test env vars
  ├── client()             → AsyncClient with app + startup patches
  └── auth_client()        → client with get_current_user overridden
        │
        └── Used by all route tests
```

The root conftest patches 3 things that would fail without a real DB:
1. `connect_mongodb` / `close_mongodb` — replaced with no-ops
2. `connect_weaviate` / `close_weaviate` — replaced with no-ops
3. `init_cover_letter_graph` — replaced with no-op (graph not built in tests)
