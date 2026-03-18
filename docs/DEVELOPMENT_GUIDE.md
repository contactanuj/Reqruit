# Development Guide

> Everything you need to contribute to Reqruit: setup, conventions, patterns, and how to extend the codebase.

---

## Table of Contents

- [Environment Setup](#environment-setup)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Code Conventions](#code-conventions)
- [Adding a New API Route](#adding-a-new-api-route)
- [Adding a New LangGraph Workflow](#adding-a-new-langgraph-workflow)
- [Adding a New Agent](#adding-a-new-agent)
- [Adding a New MongoDB Collection](#adding-a-new-mongodb-collection)
- [Known Gotchas](#known-gotchas)
- [Debugging Tips](#debugging-tips)

---

## Environment Setup

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker Desktop | latest | [docker.com](https://www.docker.com/) |

### Install

```bash
git clone https://github.com/your-username/reqruit.git
cd reqruit
uv sync
```

This creates `.venv/` and installs all dependencies from `pyproject.toml`.

### Configure

```bash
cp .env.example .env
```

Edit `.env` — minimum required:

```env
# At minimum, set this — Groq is free at console.groq.com
GROQ_API_KEY=gsk_...

# Change this from the default before running anything
JWT_SECRET_KEY=your-random-32-char-secret-here

# Optional but recommended for cover letter quality
ANTHROPIC_API_KEY=sk-ant-...
```

See the full environment variable reference in [`README.md`](../README.md#environment-variables).

---

## Running Locally

### Start Infrastructure

```bash
# MongoDB + Weaviate in the background
docker compose -f docker/docker-compose.yml up -d mongodb weaviate

# Check they're up
curl http://localhost:27017      # MongoDB
curl http://localhost:8080/v1/meta  # Weaviate
```

### Run the API

```bash
# Development (hot-reload on file changes)
uv run uvicorn src.api.main:app --reload

# Development with Docker Compose (app + infra together)
docker compose -f docker/docker-compose.dev.yml up

# Production (inside Docker)
docker compose -f docker/docker-compose.yml up
```

### Verify

```bash
# Liveness
curl http://localhost:8000/health

# Readiness (MongoDB + Weaviate connected)
curl http://localhost:8000/health/ready

# Swagger UI (dev only, requires DEBUG=true)
open http://localhost:8000/docs
```

### Stop

```bash
docker compose -f docker/docker-compose.yml down
```

---

## Testing

### Run Tests

```bash
# All unit tests (fast, no external deps)
.venv/Scripts/python.exe -m pytest tests/unit/ -q     # Windows
uv run pytest tests/unit/ -q                           # Mac/Linux

# Verbose (shows test names)
uv run pytest tests/unit/ -v

# Single module
uv run pytest tests/unit/test_llm/ -v

# Single test
uv run pytest tests/unit/test_api/test_track_routes.py::TestKanban::test_returns_all_status_groups -v

# With coverage
uv run pytest tests/unit/ --cov=src --cov-report=term-missing
```

### Test Configuration

`pytest.ini` (inside `pyproject.toml`):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"          # all async functions auto-run without decorator
testpaths = ["tests"]
filterwarnings = ["ignore::DeprecationWarning"]
```

### Fixture Hierarchy

```
tests/conftest.py
  settings()        → fresh Settings with APP_ENV=testing
  client()          → httpx.AsyncClient with patched lifespan
  auth_client()     → client with get_current_user overridden → mock User
```

The root `conftest.py` patches out all infrastructure calls in the lifespan:

```python
@pytest.fixture
async def client():
    with (
        patch("src.db.mongodb.connect_mongodb"),
        patch("src.db.mongodb.close_mongodb"),
        patch("src.db.weaviate_client.connect_weaviate"),
        patch("src.db.weaviate_client.close_weaviate"),
        patch("src.workflows.graphs.cover_letter.init_cover_letter_graph"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app)) as ac:
            yield ac
```

### Writing a Route Test

```python
# tests/unit/test_api/test_example_routes.py
from unittest.mock import AsyncMock, MagicMock
from beanie import PydanticObjectId
from httpx import AsyncClient
from src.api.dependencies import get_current_user, get_example_repository
from src.db.documents.user import User

class TestExampleRoute:
    async def test_get_returns_200(self, client: AsyncClient):
        # 1. Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = PydanticObjectId()

        # 2. Create mock repository
        mock_repo = MagicMock()
        mock_repo.find_many = AsyncMock(return_value=[...])

        # 3. Override dependencies
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_example_repository] = lambda: mock_repo

        # 4. Make request
        response = await client.get("/example")

        # 5. Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 6. Cleanup (important — prevents bleed between tests)
        client.app.dependency_overrides.clear()
```

### Writing a Service Test

```python
# tests/unit/test_services/test_example_service.py
from unittest.mock import AsyncMock, MagicMock

class TestExampleService:
    def setup_method(self):
        self.repo = MagicMock()
        self.repo.get_by_id = AsyncMock()
        self.service = ExampleService(repo=self.repo)

    async def test_does_something(self):
        self.repo.get_by_id.return_value = SomeDocument(...)
        result = await self.service.do_something("some-id")
        assert result.field == "expected"
```

### Linting

```bash
# Check
uv run ruff check src/ tests/

# Auto-fix
uv run ruff check --fix src/ tests/

# Format
uv run ruff format src/ tests/

# All three (typical pre-commit)
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
```

---

## Code Conventions

### File Layout

Every module starts with a module docstring explaining:
1. **What it does** — in one sentence
2. **Design decisions** — why this approach over alternatives
3. **Usage** — minimal code example

### Naming

| Thing | Convention | Example |
|-------|-----------|---------|
| Route files | `noun.py` | `jobs.py`, `profile.py` |
| Repository files | `{noun}_repository.py` | `job_repository.py` |
| Test files | `test_{module}.py` | `test_job_repository.py` |
| Test classes | `Test{WhatYouTest}` | `TestJobRepository` |
| Test methods | `test_{scenario}` | `test_returns_404_when_not_found` |
| Error codes | `UPPER_SNAKE_CASE` | `JOB_NOT_FOUND`, `INVALID_STATUS_TRANSITION` |

### Exception Hierarchy

Always raise from the domain exception hierarchy — never `raise HTTPException()` in services:

```python
# Good — service layer
raise NotFoundError("Job", job_id)               # → 404 JOB_NOT_FOUND
raise BusinessValidationError("Cannot apply...", "DUPLICATE_APPLICATION")  # → 422

# Bad — HTTP in services
raise HTTPException(status_code=404, detail="Not found")
```

### Async Everywhere

All I/O must be `async/await`. Never use synchronous DB calls, `requests.get()`, or `time.sleep()` in async code.

```python
# Good
async def get_job(job_id: str) -> Job:
    return await Job.get(PydanticObjectId(job_id))

# Bad — blocks the event loop
def get_job_sync(job_id: str) -> Job:
    return Job.find_one({"_id": job_id}).run_sync()
```

### Owner Scoping — Non-Negotiable

Every resource query that returns user data MUST scope to `user_id`. This is enforced at the repository layer:

```python
# Always scope to user_id
async def get_by_user_and_id(self, user_id, resource_id):
    return await Model.find_one({"_id": resource_id, "user_id": user_id})

# Never return without owner check
async def get_by_id_unsafe(self, resource_id):  # ← WRONG
    return await Model.get(resource_id)
```

### Structured Logging

Use `structlog` with key=value pairs — never string interpolation:

```python
logger.info(
    "cover_letter_approved",           # event name: snake_case verb_noun
    user_id=str(current_user.id),      # always include user_id
    application_id=application_id,
    thread_id=body.thread_id,
)

# Not this:
logger.info(f"Cover letter approved for user {user_id}")
```

---

## Adding a New API Route

Follow these 6 steps. Example: adding a `PATCH /profile/preferences` endpoint.

### Step 1: Add request/response schemas to the route file

```python
# src/api/routes/profile.py
class UpdatePreferencesRequest(BaseModel):
    remote: RemotePreference | None = None
    min_salary: int | None = None
    locations: list[str] | None = None
```

### Step 2: Add repository method if needed

```python
# src/repositories/profile_repository.py
async def update_preferences(
    self, user_id: PydanticObjectId, preferences: dict
) -> Profile | None:
    profile = await self.get_by_user_id(user_id)
    if profile:
        await profile.update({"$set": {f"preferences.{k}": v
                               for k, v in preferences.items() if v is not None}})
    return profile
```

### Step 3: Add the route handler

```python
@router.patch("/profile/preferences", response_model=ProfileResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    """Update the user's job preferences."""
    profile = await profile_repo.update_preferences(
        current_user.id, body.model_dump(exclude_none=True)
    )
    if not profile:
        raise NotFoundError("Profile")
    return ProfileResponse.model_validate(profile.model_dump())
```

### Step 4: Add dependency function (if new repository)

```python
# src/api/dependencies.py
def get_example_repository() -> ExampleRepository:
    """Provide an ExampleRepository instance."""
    return ExampleRepository()
```

### Step 5: Register router in main.py (if new router file)

```python
# src/api/main.py → _register_routes()
application.include_router(example_router)
```

### Step 6: Write tests

```python
# tests/unit/test_api/test_profile_routes.py
async def test_update_preferences_returns_updated_profile(self, client):
    mock_user = MagicMock(spec=User, id=PydanticObjectId())
    mock_profile = MagicMock(spec=Profile)
    mock_repo = MagicMock()
    mock_repo.update_preferences = AsyncMock(return_value=mock_profile)

    client.app.dependency_overrides[get_current_user] = lambda: mock_user
    client.app.dependency_overrides[get_profile_repository] = lambda: mock_repo

    response = await client.patch(
        "/profile/preferences",
        json={"remote": "hybrid", "min_salary": 200000}
    )

    assert response.status_code == 200
    client.app.dependency_overrides.clear()
```

---

## Adding a New LangGraph Workflow

Example: adding a `tailored_resume` workflow.

### Step 1: Define the state

```python
# src/workflows/states/tailored_resume.py
from typing import TypedDict

class TailoredResumeState(TypedDict):
    job_description: str
    original_resume: str
    requirements_analysis: str   # from RequirementsAnalyst
    tailored_resume: str         # from ResumeTailor
    feedback: str
    status: str
```

### Step 2: Build the graph

```python
# src/workflows/graphs/tailored_resume.py
_compiled_graph: CompiledStateGraph | None = None

def build_tailored_resume_graph(checkpointer) -> CompiledStateGraph:
    builder = StateGraph(TailoredResumeState)
    builder.add_node("analyze_requirements", analyze_requirements_node)
    builder.add_node("tailor_resume", tailor_resume_node)
    builder.add_node("human_review", human_review_node)
    builder.add_edge(START, "analyze_requirements")
    builder.add_edge("analyze_requirements", "tailor_resume")
    builder.add_edge("tailor_resume", "human_review")
    return builder.compile(checkpointer=checkpointer)

def init_tailored_resume_graph(checkpointer):
    global _compiled_graph
    _compiled_graph = build_tailored_resume_graph(checkpointer)

def get_tailored_resume_graph() -> CompiledStateGraph:
    if _compiled_graph is None:
        raise RuntimeError("Graph not initialized")
    return _compiled_graph
```

### Step 3: Initialize at startup

```python
# src/api/main.py → lifespan()
from src.workflows.graphs.tailored_resume import init_tailored_resume_graph
init_tailored_resume_graph(get_checkpointer())
```

### Step 4: Add routes

Follow the same pattern as `src/api/routes/apply.py`:
- `POST` — create DocumentRecord, return `thread_id`, status 202
- `GET` — SSE stream, run graph, emit events
- `POST /review` — resume with `Command(resume=...)`

---

## Adding a New Agent

### Step 1: Define the agent class

```python
# src/agents/resume_tailor.py
from src.agents.base import BaseAgent
from src.llm.models import TaskType

class ResumeTailor(BaseAgent):
    def __init__(self):
        super().__init__(
            name="resume_tailor",
            task_type=TaskType.RESUME_TAILORING,
            system_prompt="""You are an expert resume writer...

            Given a job description and original resume, tailor the resume
            to highlight relevant experience and skills.

            Return only the tailored resume text.""",
        )

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        # Build messages from state
        messages = self._build_messages(state)
        # Call LLM via base class helper
        response = await self._invoke(messages, config)
        return {"tailored_resume": response.content}
```

### Step 2: Add task type to routing table

```python
# src/llm/models.py
class TaskType(StrEnum):
    ...
    RESUME_TAILORING = "resume_tailoring"

ROUTING_TABLE: dict[TaskType, list[ModelConfig]] = {
    ...
    TaskType.RESUME_TAILORING: [
        ModelConfig(ProviderName.ANTHROPIC, "claude-sonnet-4-5", max_tokens=4000, temperature=0.3),
        ModelConfig(ProviderName.OPENAI,    "gpt-4o",            max_tokens=4000, temperature=0.3),
    ],
}
```

### Step 3: Add memory recipe

```python
# src/memory/recipes.py
MEMORY_RECIPES: dict[str, MemoryRecipe] = {
    ...
    "resume_tailor": MemoryRecipe(
        weaviate_collections=["ResumeChunk", "JobEmbedding"],
        recency_collections=[],
        relevance_weight=0.8,
        recency_weight=0.2,
        max_items=10,
    ),
}
```

### Step 4: Write unit tests

Test the agent with mocked LLM responses — never make real API calls in unit tests:

```python
# tests/unit/test_agents/test_resume_tailor.py
from unittest.mock import AsyncMock, patch

async def test_returns_tailored_resume():
    agent = ResumeTailor()
    mock_response = MagicMock()
    mock_response.content = "Tailored resume content here..."

    with patch.object(agent, "_invoke", new=AsyncMock(return_value=mock_response)):
        result = await agent(
            {"job_description": "Senior Python Engineer...", "original_resume": "..."},
            config={"configurable": {"user_id": "test-user"}}
        )

    assert "tailored_resume" in result
    assert len(result["tailored_resume"]) > 0
```

---

## Adding a New MongoDB Collection

### Step 1: Create the document model

```python
# src/db/documents/interview_prep.py
from beanie import Document
from pydantic import Field
from src.db.base_document import TimestampedDocument

class InterviewPrep(TimestampedDocument):
    user_id: PydanticObjectId
    application_id: PydanticObjectId
    company_brief: str = ""
    predicted_questions: list[str] = Field(default_factory=list)

    class Settings:
        name = "interview_prep"
        indexes = [
            IndexModel([("application_id", ASCENDING)], name="application_idx"),
        ]
```

### Step 2: Register with Beanie

```python
# src/db/mongodb.py → connect_mongodb()
document_models = [
    User, Profile, Resume, Job, Company, Contact,
    Application, DocumentRecord, OutreachMessage,
    Interview, STARStory, LLMUsage,
    InterviewPrep,   # ← add here
]
await init_beanie(database=db, document_models=document_models)
```

### Step 3: Create the repository

```python
# src/repositories/interview_prep_repository.py
from src.repositories.base import BaseRepository
from src.db.documents.interview_prep import InterviewPrep

class InterviewPrepRepository(BaseRepository[InterviewPrep]):
    _model = InterviewPrep

    async def get_for_application(self, application_id: PydanticObjectId):
        return await InterviewPrep.find_one({"application_id": application_id})
```

### Step 4: Add dependency

```python
# src/api/dependencies.py
def get_interview_prep_repository() -> InterviewPrepRepository:
    return InterviewPrepRepository()
```

---

## Known Gotchas

### 1. Pydantic Settings `default_factory`

Sub-settings in `Settings` MUST use `Field(default_factory=SubClass)`, not `SubClass()`:

```python
# WRONG — evaluated once at class definition time
class Settings(BaseSettings):
    app: AppSettings = AppSettings()   # ← broken: cache_clear() won't work

# CORRECT
class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
```

### 2. `uv run pytest` on Windows

On Windows, `uv run pytest` sometimes fails with a trampoline error. Use the venv directly:

```bash
.venv/Scripts/python.exe -m pytest tests/unit/ -q
```

### 3. `AsyncMock` as FastAPI Dependency Override

Using `AsyncMock` directly as a dependency override causes 422 validation errors:

```python
# WRONG
app.dependency_overrides[get_current_user] = AsyncMock(return_value=mock_user)

# CORRECT — use a lambda that returns the value
app.dependency_overrides[get_current_user] = lambda: mock_user
```

### 4. JWT Token Type Check

The `get_current_user` dependency checks `payload.get("type") != "access"` before any DB lookup. Tests using refresh tokens as access tokens will get 401, not find the user.

### 5. structlog `add_logger_name`

`structlog.stdlib.add_logger_name` is incompatible with `PrintLoggerFactory`. It's been removed from `configure_logging()`. Do not add it back.

### 6. Weaviate Docker Registry

`cr.weaviate.io` (Weaviate's own registry) can return 500 errors. Use `semitechnologies/weaviate` from Docker Hub instead:

```yaml
# docker-compose.yml
image: semitechnologies/weaviate:1.28.4   # ← correct
# NOT: cr.weaviate.io/semitechnologies/weaviate:1.28.4
```

### 7. Beanie 2.0 vs Motor

Beanie 2.0 uses PyMongo's native async API directly — NOT Motor. Import paths that reference Motor will fail. The async client is `AsyncIOMotorClient` is not used; Beanie 2.0 abstracts this.

### 8. LangGraph Checkpointer in Tests

Tests must use `MemorySaver` (in-memory), not `MongoDBSaver` (requires real MongoDB):

```python
from langgraph.checkpoint.memory import MemorySaver
graph = build_cover_letter_graph(MemorySaver())
```

---

## Debugging Tips

### Check Application Startup

```bash
uv run uvicorn src.api.main:app --reload --log-level debug
```

Startup logs show which LLM providers were detected:

```
model_manager_initialized available_providers=["groq"] provider_count=1
cover_letter_graph_initialized
application_startup app_name=reqruit environment=development
```

### Test a Specific Endpoint

```bash
# Register
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "password123"}' | jq

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "password123"}' | jq -r .access_token)

# Use token
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Inspect MongoDB

```bash
# Connect to MongoDB shell in Docker
docker exec -it reqruit-mongodb-1 mongosh

# Switch to the app database
use job_hunt

# List collections
show collections

# View users
db.users.find().pretty()
```

### Inspect LangGraph Checkpoints

```bash
# Checkpoints are stored in the "checkpoints" collection in MongoDB
db.checkpoints.find({thread_id: "your-thread-id"}).pretty()
```

### Enable LangSmith Tracing

```env
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=reqruit-dev
```

All LangChain/LangGraph calls will appear at [smith.langchain.com](https://smith.langchain.com). Free tier: 5K traces/month.

### Run a Single Failing Test with Full Output

```bash
uv run pytest tests/unit/test_api/test_apply_routes.py::TestCoverLetterStream::test_streams_node_events -v -s
```

The `-s` flag disables stdout capture so `print()` statements and structlog output are visible.
