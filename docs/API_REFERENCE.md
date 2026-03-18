# API Reference

> Complete endpoint reference for Reqruit's REST API.
> Base URL: `http://localhost:8000` (development)

All authenticated endpoints require `Authorization: Bearer <access_token>`.

**Error response format (all endpoints):**

```json
{
  "error_code": "UPPER_SNAKE_CASE_CODE",
  "detail": "Human-readable description"
}
```

---

## Table of Contents

- [Auth](#auth)
- [Profile](#profile)
- [Jobs](#jobs)
- [Apply](#apply)
- [Track](#track)
- [System](#system)
- [Error Codes Reference](#error-codes-reference)

---

## Auth

### POST `/auth/register`

Register a new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response `201`:**

```json
{
  "id": "60a7f9b8c7e4f2001c4e1234",
  "email": "user@example.com",
  "created_at": "2026-03-12T10:00:00Z"
}
```

**Errors:** `409 EMAIL_ALREADY_REGISTERED`

---

### POST `/auth/login`

Authenticate and receive tokens.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response `200`:**

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Errors:** `401 AUTH_INVALID_CREDENTIALS`

---

### POST `/auth/refresh`

Rotate the token pair using a valid refresh token. Uses server-side token family tracking with atomic CAS revocation (RFC 6749 Section 10.4 compliant).

**Rotation behavior:**

1. The old refresh token is atomically invalidated (compare-and-swap)
2. A new access + refresh token pair is returned
3. The new refresh token belongs to the same family as the old one
4. If an already-revoked token is reused, the entire token family is revoked (theft detection)

**Request:**

```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response `200`:**

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Errors:**

- `401 AUTH_TOKEN_EXPIRED` — refresh token JWT has expired
- `401 AUTH_TOKEN_INVALID` — token reuse detected (family revoked), old-format token without JTI, or invalid token

---

### GET `/auth/me`

Return the current authenticated user.

**Auth:** Required

**Response `200`:**

```json
{
  "id": "60a7f9b8c7e4f2001c4e1234",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-03-12T10:00:00Z"
}
```

---

## Profile

### GET `/profile`

Return the current user's career profile. Auto-creates an empty profile on first call.

**Auth:** Required

**Response `200`:**

```json
{
  "id": "...",
  "user_id": "...",
  "headline": "Senior Software Engineer",
  "summary": "10 years building distributed systems...",
  "skills": ["Python", "FastAPI", "Kubernetes"],
  "target_roles": ["Staff Engineer", "Principal Engineer"],
  "target_companies": ["Stripe", "Anthropic"],
  "preferences": {
    "remote": "remote",
    "min_salary": 180000,
    "locations": ["San Francisco", "Remote"]
  }
}
```

---

### PATCH `/profile`

Update profile fields (partial update — only provided fields are changed).

**Auth:** Required

**Request (all fields optional):**

```json
{
  "headline": "Principal Engineer",
  "skills": ["Python", "Go", "Rust"],
  "target_roles": ["Staff Engineer"],
  "preferences": {
    "remote": "hybrid",
    "min_salary": 200000
  }
}
```

**Response `200`:** Updated profile object (same schema as GET `/profile`)

---

### GET `/profile/resumes`

List all resumes for the current user.

**Auth:** Required

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Max results (1–50) |

**Response `200`:**

```json
[
  {
    "id": "...",
    "filename": "resume_v3.pdf",
    "is_master": true,
    "parse_status": "completed",
    "created_at": "2026-03-10T14:22:00Z"
  }
]
```

**`parse_status` values:** `pending`, `processing`, `completed`, `failed`

---

### POST `/profile/resumes/upload`

Upload a resume file. Parsing runs asynchronously in the background.

**Auth:** Required

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF or DOCX, max 10MB |
| `is_master` | bool | No | Set as master resume (default: false) |

**Response `202`:**

```json
{
  "id": "60a7f9b8c7e4f2001c4e5678",
  "filename": "resume_v3.pdf",
  "parse_status": "pending",
  "message": "Resume uploaded. Parsing in progress."
}
```

**Notes:**
- Returns `202 Accepted` immediately — parsing is a background task
- Poll `GET /profile/resumes/{id}/parse-status` to track completion
- If `is_master=true`, all other resumes for this user are unset from master atomically

**Errors:** `422 INVALID_FILE_TYPE`, `422 FILE_TOO_LARGE`

---

### GET `/profile/resumes/{id}/parse-status`

Poll the parsing status of an uploaded resume.

**Auth:** Required

**Response `200`:**

```json
{
  "id": "...",
  "parse_status": "completed",
  "parsed_at": "2026-03-10T14:22:05Z"
}
```

**Errors:** `404 RESUME_NOT_FOUND`, `403 FORBIDDEN`

---

### GET `/profile/resumes/{id}`

Return a single resume with full parsed data.

**Auth:** Required

**Response `200`:**

```json
{
  "id": "...",
  "filename": "resume_v3.pdf",
  "raw_text": "John Doe\nSenior Engineer...",
  "is_master": true,
  "parse_status": "completed",
  "parsed_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "skills": ["Python", "FastAPI"],
    "experience": [...],
    "education": [...]
  }
}
```

**Errors:** `404 RESUME_NOT_FOUND`, `403 FORBIDDEN`

---

### PATCH `/profile/resumes/{id}`

Update resume metadata (e.g., set as master).

**Auth:** Required

**Request:**

```json
{
  "is_master": true
}
```

**Response `200`:** Updated resume object

**Errors:** `404 RESUME_NOT_FOUND`, `403 FORBIDDEN`

---

### DELETE `/profile/resumes/{id}`

Delete a resume. Cannot delete a resume that is the only one.

**Auth:** Required

**Response `204`:** No content

**Errors:** `404 RESUME_NOT_FOUND`, `403 FORBIDDEN`

---

## Jobs

### POST `/jobs/manual`

Manually add a job and create an application in `SAVED` status atomically.

**Auth:** Required

**Request:**

```json
{
  "title": "Senior Backend Engineer",
  "company_name": "Anthropic",
  "description": "We are looking for...",
  "url": "https://boards.greenhouse.io/anthropic/jobs/123",
  "location": "San Francisco, CA",
  "remote": "hybrid",
  "salary_min": 180000,
  "salary_max": 250000,
  "requirements": {
    "required_skills": ["Python", "Distributed Systems"],
    "years_experience": 5,
    "education": "BS Computer Science"
  }
}
```

**Response `201`:**

```json
{
  "job_id": "...",
  "application_id": "...",
  "status": "saved"
}
```

---

### GET `/jobs`

List all jobs the user has saved, with two-query pattern (no N+1).

**Auth:** Required

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 20 | Max results (1–100) |

**Response `200`:**

```json
[
  {
    "job_id": "...",
    "application_id": "...",
    "title": "Senior Backend Engineer",
    "company_name": "Anthropic",
    "status": "saved",
    "location": "San Francisco, CA",
    "remote": "hybrid",
    "created_at": "2026-03-10T14:22:00Z"
  }
]
```

---

### GET `/jobs/{id}`

Return a single job with its application.

**Auth:** Required

**Response `200`:**

```json
{
  "job_id": "...",
  "application_id": "...",
  "title": "Senior Backend Engineer",
  "company_name": "Anthropic",
  "description": "We are looking for...",
  "url": "...",
  "location": "San Francisco, CA",
  "remote": "hybrid",
  "salary_min": 180000,
  "salary_max": 250000,
  "requirements": { ... },
  "status": "saved",
  "notes": "Met CTO at conference",
  "created_at": "..."
}
```

**Errors:** `404 JOB_NOT_FOUND`, `403 FORBIDDEN`

---

### DELETE `/jobs/{id}`

Delete a job and cascade-delete all associated data.

**Cascade order:**

1. Fetch cover letter document IDs for Weaviate cleanup
2. Delete CoverLetterEmbeddings from Weaviate (non-blocking)
3. Delete DocumentRecords, OutreachMessages, Interviews from MongoDB
4. Delete the Application
5. Delete JobEmbeddings from Weaviate (non-blocking)
6. Delete the Job

Weaviate failures are non-blocking (logged as warnings, never fail the request).

**Auth:** Required

**Response `204`:** No content

**Errors:** `404 JOB_NOT_FOUND`, `403 FORBIDDEN`

---

### GET `/jobs/{id}/contacts`

List contacts at the job's company.

**Auth:** Required

**Response `200`:**

```json
[
  {
    "id": "...",
    "name": "Jane Smith",
    "title": "Engineering Manager",
    "linkedin_url": "https://linkedin.com/in/janesmith",
    "email": "jane@anthropic.com",
    "type": "manager",
    "notes": "Spoke at PyCon 2025"
  }
]
```

---

### POST `/jobs/{id}/contacts`

Add a contact for a job's company. Creates the company record if it doesn't exist.

**Auth:** Required

**Request:**

```json
{
  "name": "Jane Smith",
  "title": "Engineering Manager",
  "linkedin_url": "https://linkedin.com/in/janesmith",
  "email": "jane@anthropic.com",
  "type": "manager",
  "notes": "Spoke at PyCon 2025"
}
```

**`type` values:** `recruiter`, `engineer`, `manager`, `generic`

**Response `201`:** Created contact object

---

### PATCH `/jobs/{id}/contacts/{contact_id}`

Update a contact's details.

**Auth:** Required

**Request (all fields optional):**

```json
{
  "title": "Senior Engineering Manager",
  "notes": "Follow up after interview"
}
```

**Response `200`:** Updated contact object

---

## Apply

### GET `/apply/applications/{application_id}/documents`

List all AI-generated documents for an application.

**Auth:** Required

**Response `200`:**

```json
[
  {
    "id": "...",
    "doc_type": "cover_letter",
    "version": 2,
    "is_approved": false,
    "content_preview": "Dear Hiring Manager, I am excited to apply...",
    "created_at": "2026-03-12T10:00:00Z"
  }
]
```

**`doc_type` values:** `cover_letter`, `tailored_resume`, `outreach_message`

---

### POST `/apply/applications/{application_id}/cover-letter`

Start the cover letter generation workflow. Returns immediately with a `thread_id`.

**Auth:** Required

**Request:**

```json
{
  "resume_id": "60a7f9b8c7e4f2001c4e5678"
}
```

`resume_id` is optional. Omit to use the master resume.

**Response `202`:**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "60a7f9b8c7e4f2001c4e9999",
  "version": 1,
  "status": "started"
}
```

**Errors:**

| Code | Status | Condition |
|------|--------|-----------|
| `GENERATION_ALREADY_IN_PROGRESS` | 409 | An in-progress generation exists for this application (response includes existing `thread_id` in detail) |
| `RATE_LIMITED` | 429 | User has exceeded the per-hour LLM request limit. Response includes `Retry-After` header (seconds) |
| `APPLICATION_NOT_FOUND` | 404 | Application does not exist or belongs to another user |
| `JOB_NOT_FOUND` | 404 | The application's linked job record is missing |

**Next step:** Open the SSE stream endpoint with this `thread_id`.

---

### GET `/apply/applications/{application_id}/cover-letter/stream`

SSE stream for cover letter generation with reconnect support. Opens a persistent connection and emits workflow events in real-time. On reconnect, the endpoint detects existing checkpoint state and adapts behavior accordingly.

**Auth:** Required

**Query parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `thread_id` | string | Yes | From the POST response above |

**Response:** `text/event-stream`

**Fresh start** (no checkpoint exists):

```text
data: {"event": "node_complete", "node": "analyze_requirements"}

data: {"event": "node_complete", "node": "retrieve_memories"}

data: {"event": "node_complete", "node": "write_cover_letter"}

data: {
  "event": "awaiting_review",
  "cover_letter": "Dear Hiring Manager...",
  "requirements_analysis": "Key requirements: Python 5+ years...",
  "thread_id": "550e8400-..."
}
```

The stream closes after `awaiting_review`. The LangGraph workflow is paused at the human review checkpoint.

**Reconnect scenarios:**

The endpoint checks checkpoint state via `graph.aget_state()` before streaming. This handles three reconnect cases:

| Scenario | Checkpoint state | Behavior |
|----------|-----------------|----------|
| **Awaiting review** | `next=("human_review",)` | Emits `awaiting_review` event immediately from saved state. Graph is NOT re-executed. |
| **In-flight** | `next` is a non-interrupt node | Resumes graph from last checkpoint (`astream(None, config)`). No duplicate node execution. |
| **Completed** | `values` populated, `next=()` | Emits a single `completed` event. |

Reconnect at interrupt example (single event, no node_complete):

```text
data: {
  "event": "awaiting_review",
  "cover_letter": "Dear Hiring Manager...",
  "requirements_analysis": "Key requirements: Python 5+ years...",
  "thread_id": "550e8400-..."
}
```

Completed graph reconnect:

```text
data: {"event": "completed", "thread_id": "550e8400-..."}
```

**On error:**

```text
data: {"event": "error", "detail": "LLM provider unavailable"}
```

**Errors:** `403 FORBIDDEN` (thread_id belongs to another user or application_id mismatch), `404 DOCUMENT_NOT_FOUND` (thread_id does not exist), `404 APPLICATION_NOT_FOUND`

**Next step:** Call `POST /cover-letter/review` with `action: approve` or `action: revise`.

---

### POST `/apply/applications/{application_id}/cover-letter/review`

Resume the workflow after human review. Approve the draft or request a revision.

**Auth:** Required

**Request (approve):**

```json
{
  "thread_id": "550e8400-...",
  "action": "approve"
}
```

**Response `200`:**

```json
{
  "status": "approved",
  "document_id": "60a7f9b8c7e4f2001c4e9999"
}
```

**Request (revise):**

```json
{
  "thread_id": "550e8400-...",
  "action": "revise",
  "feedback": "Make it shorter and more focused on the ML experience. Remove the third paragraph."
}
```

**Response `200`:**

```json
{
  "status": "revision_started",
  "thread_id": "550e8400-..."
}
```

**After revise:** Re-open the SSE stream with the same `thread_id` to receive the revised draft.

**Checkpoint Validation Errors (422):**

| Error Code | Condition | Detail |
|-----------|-----------|--------|
| `THREAD_NOT_FOUND` | No checkpoint exists (never started or deleted) | `"No active workflow session found for this thread"` |
| `THREAD_EXPIRED` | Checkpoint exists but graph already completed | `"Workflow session has expired or already completed"` |
| `THREAD_NOT_READY` | Graph is still processing (not at human review) | `"Workflow is still processing — please wait for the draft to complete"` |
| `INVALID_ACTION` | Action is not `approve` or `revise` | `"Action must be 'approve' or 'revise'"` |

**Error response format:**

```json
{
  "error_code": "THREAD_NOT_FOUND",
  "detail": "No active workflow session found for this thread"
}
```

**Other Errors:** `403 FORBIDDEN` (thread_id belongs to another user or application_id mismatch), `404 DOCUMENT_NOT_FOUND` (thread_id does not exist), `404 APPLICATION_NOT_FOUND`

---

## Track

### GET `/track/kanban`

Return all applications grouped by status for a Kanban board. Single query + batch join (no N+1).

**Auth:** Required

**Response `200`:**

```json
{
  "saved": [
    {
      "application_id": "...",
      "job_id": "...",
      "job_title": "Senior Backend Engineer",
      "company_name": "Anthropic",
      "status": "saved",
      "applied_at": null,
      "notes": "",
      "created_at": "2026-03-10T14:22:00Z"
    }
  ],
  "applied": [...],
  "interviewing": [...],
  "offered": [...],
  "accepted": [...],
  "rejected": [...],
  "withdrawn": [...]
}
```

All 7 status keys are always present (empty array if no applications in that status).

---

### GET `/track/applications`

Paginated list of applications with optional status filter.

**Auth:** Required

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status` | string | — | Filter by status (`saved`, `applied`, etc.) |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Max results (1–100) |

**Response `200`:** Array of `KanbanItem` objects (same schema as kanban board items).

---

### PATCH `/track/applications/{application_id}/status`

Transition an application to a new status. Enforces the state machine — invalid transitions are rejected.

**Auth:** Required

**Request:**

```json
{
  "status": "applied"
}
```

**Response `200`:**

```json
{
  "application_id": "...",
  "old_status": "saved",
  "new_status": "applied"
}
```

**State machine (valid transitions):**

```
SAVED       → applied, withdrawn
APPLIED     → interviewing, rejected, withdrawn
INTERVIEWING → offered, rejected, withdrawn
OFFERED     → accepted, rejected, withdrawn
ACCEPTED    → (terminal — no transitions)
REJECTED    → (terminal — no transitions)
WITHDRAWN   → (terminal — no transitions)
```

**Side effect:** When transitioning to `APPLIED`, `applied_at` is set to the current timestamp if not already set.

**Errors:** `404 APPLICATION_NOT_FOUND`, `422 INVALID_STATUS_TRANSITION`

---

### PATCH `/track/applications/{application_id}/notes`

Update personal notes on an application. Separate from status to prevent accidental overwrites.

**Auth:** Required

**Request:**

```json
{
  "notes": "Had a great call with the hiring manager. They want Python + distributed systems experience."
}
```

**Response `200`:**

```json
{
  "application_id": "...",
  "notes": "Had a great call with the hiring manager..."
}
```

**Errors:** `404 APPLICATION_NOT_FOUND`

---

## System

### GET `/health`

Liveness check — returns 200 if the process is alive. Used by Docker HEALTHCHECK and load balancers.

**Auth:** Not required

**Response `200`:**

```json
{
  "status": "healthy",
  "app": "reqruit",
  "version": "0.1.0",
  "environment": "development"
}
```

---

### GET `/health/ready`

Readiness check — verifies MongoDB and Weaviate are reachable. Used by orchestrators before routing traffic.

**Auth:** Not required

**Response `200` (ready):**

```json
{
  "status": "ready",
  "mongodb": { "status": "ok", "latency_ms": 2 },
  "weaviate": { "status": "ok", "latency_ms": 5 }
}
```

**Response `503` (not ready):**

```json
{
  "status": "not ready",
  "mongodb": { "status": "ok", "latency_ms": 2 },
  "weaviate": { "status": "error", "detail": "Connection refused" }
}
```

---

## Error Codes Reference

| Code | HTTP | Raised By |
|------|------|-----------|
| `AUTH_FAILED` | 401 | `get_current_user` — generic auth failure |
| `AUTH_TOKEN_EXPIRED` | 401 | `get_current_user` — JWT past expiry |
| `AUTH_TOKEN_INVALID` | 401 | `get_current_user` — malformed token or wrong type |
| `AUTH_USER_NOT_FOUND` | 401 | `get_current_user` — user deleted after token issued |
| `AUTH_ACCOUNT_INACTIVE` | 401 | `get_current_user` — account soft-deleted |
| `AUTH_INVALID_CREDENTIALS` | 401 | `POST /auth/login` — wrong email/password |
| `FORBIDDEN` | 403 | Owner-scope check fails (resource belongs to another user) |
| `*_NOT_FOUND` | 404 | `NotFoundError(resource)` — `JOB_NOT_FOUND`, `RESUME_NOT_FOUND`, etc. |
| `EMAIL_ALREADY_REGISTERED` | 409 | `POST /auth/register` — duplicate email |
| `CONFLICT` | 409 | Generic conflict (e.g., duplicate application) |
| `DOCUMENT_VERSION_CONFLICT` | 409 | Concurrent document version collision (retry exhausted) |
| `INVALID_STATUS_TRANSITION` | 422 | `PATCH /track/.../status` — illegal state machine move |
| `INVALID_ACTION` | 422 | `POST /apply/.../review` — action not `approve` or `revise` |
| `VALIDATION_FAILED` | 422 | Business rule violation |
| `RATE_LIMITED` | 429 | LLM rate limit or user monthly budget exceeded |
| `LLM_PROVIDER_ERROR` | 502 | LLM API call failed |
| `LLM_ALL_PROVIDERS_UNAVAILABLE` | 502 | All configured providers failed or have open circuits |
| `DATABASE_ERROR` | 500 | MongoDB operation failed unexpectedly |
| `VECTOR_SEARCH_ERROR` | 500 | Weaviate search failed |
| `EMBEDDING_ERROR` | 500 | BGE embedding generation failed |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

> Pydantic schema validation errors (`RequestValidationError`) return `422` with FastAPI's default format — not the `error_code` format above. These cover malformed JSON, missing required fields, and type errors at the API boundary.
