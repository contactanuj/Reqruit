# Data Model Reference

> Complete schema reference for Reqruit's MongoDB collections and Weaviate vector collections.

---

## Table of Contents

- [Design Principles](#design-principles)
- [MongoDB Collections](#mongodb-collections)
  - [users](#users)
  - [profiles](#profiles)
  - [resumes](#resumes)
  - [jobs](#jobs)
  - [companies](#companies)
  - [contacts](#contacts)
  - [applications](#applications)
  - [documents](#documents)
  - [outreach_messages](#outreach_messages)
  - [interviews](#interviews)
  - [star_stories](#star_stories)
  - [llm_usage](#llm_usage)
- [Weaviate Collections](#weaviate-collections)
- [Enumerations](#enumerations)
- [Collection Relationships](#collection-relationships)

---

## Design Principles

### Document vs Reference

Reqruit uses a hybrid embedding strategy:

- **Embed** (nest as subdocument): small, tightly coupled data that is always read with the parent. Example: `Job.requirements` — always displayed with the job.
- **Reference** (separate collection): large or independently queryable data. Example: `Resume` is referenced from `Application` by ID — resumes can be listed, updated, and versioned independently.

### Timestamps

Every collection inherits from `TimestampedDocument`, which adds `created_at` and `updated_at` via Beanie lifecycle hooks:

```python
@before_event(Insert)
def set_created():
    self.created_at = datetime.now(UTC)

@before_event(Insert, Save, Replace)
def set_updated():
    self.updated_at = datetime.now(UTC)
```

### Owner Scoping

Every document that belongs to a user has a `user_id: PydanticObjectId` field. All repository query methods always include `user_id` in the filter — data from different users never leaks across queries.

---

## MongoDB Collections

### users

Authentication identity. Does not store profile data (that's in `profiles`).

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | Auto-generated |
| `email` | string | Unique index |
| `hashed_password` | string | bcrypt, never returned by API |
| `is_active` | bool | Default: `true`. Set to `false` for soft-delete |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Indexes:**
- `email` — unique index (enforces no duplicate registrations)

---

### profiles

Career data for a user. One profile per user, auto-created on first `GET /profile`.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id`, unique |
| `headline` | string | e.g., "Senior Software Engineer" |
| `summary` | string | Elevator pitch / professional summary |
| `skills` | `list[string]` | Flat skill list, deduplicated |
| `certifications` | `list[string]` | |
| `target_roles` | `list[string]` | e.g., ["Staff Engineer", "Tech Lead"] |
| `target_companies` | `list[string]` | |
| `preferences` | embedded `UserPreferences` | See below |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**UserPreferences (embedded):**

| Field | Type | Notes |
|-------|------|-------|
| `remote` | `RemotePreference` | `remote`, `hybrid`, `onsite`, `no_preference` |
| `min_salary` | int | Annual, USD |
| `locations` | `list[string]` | Acceptable locations |
| `open_to_relocation` | bool | Default: `false` |

**Indexes:**
- `user_id` — unique index

---

### resumes

Uploaded resume documents with parsed structured data.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `filename` | string | Original uploaded filename |
| `raw_text` | string | Full text extracted from PDF/DOCX |
| `is_master` | bool | One master resume per user |
| `parse_status` | string | `pending`, `processing`, `completed`, `failed` |
| `parsed_at` | datetime | Nullable — set when parsing completes |
| `parsed_data` | embedded `ParsedResume` | Structured extracted data |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**ParsedResume (embedded):**

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | |
| `email` | string | |
| `phone` | string | |
| `linkedin` | string | |
| `skills` | `list[string]` | |
| `experience` | `list[WorkExperience]` | |
| `education` | `list[Education]` | |

**Indexes:**
- `user_id` — for `get_all_for_user()`
- `(user_id, is_master)` — for `get_master_resume()`

---

### jobs

Job listings manually added or discovered by the JobSearcher agent.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` (owner) |
| `title` | string | e.g., "Senior Backend Engineer" |
| `company_name` | string | Denormalized for display without join |
| `company_id` | ObjectId | Nullable — ref: `companies._id` |
| `description` | string | Full job description text |
| `url` | string | Source URL |
| `location` | string | |
| `remote` | `RemotePreference` | |
| `salary_min` | int | Annual USD, nullable |
| `salary_max` | int | Annual USD, nullable |
| `requirements` | embedded `JobRequirements` | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**JobRequirements (embedded):**

| Field | Type | Notes |
|-------|------|-------|
| `required_skills` | `list[string]` | |
| `preferred_skills` | `list[string]` | |
| `years_experience` | int | Nullable |
| `education` | string | e.g., "BS Computer Science" |
| `responsibilities` | `list[string]` | |

**Indexes:**
- `user_id` — for `get_for_user()`

---

### companies

Company records created when a contact is added to a job. One record per unique company name per user.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `name` | string | Company name |
| `website` | string | |
| `industry` | string | |
| `size` | string | e.g., "201-500 employees" |
| `hq_location` | string | |
| `tech_stack` | `list[string]` | Technologies used |
| `research_notes` | string | AI-generated company brief |
| `culture_notes` | string | Glassdoor/interview feedback |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Indexes:**
- `(user_id, name)` — for `get_by_name()` (lazy company creation)

---

### contacts

Individual contacts at companies. Used for outreach workflow.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `company_id` | ObjectId | Ref: `companies._id` |
| `name` | string | |
| `title` | string | e.g., "Engineering Manager" |
| `linkedin_url` | string | |
| `email` | string | |
| `type` | `MessageType` | `recruiter`, `engineer`, `manager`, `generic` |
| `notes` | string | Free-form notes |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Indexes:**
- `company_id` — for `get_for_company()`

---

### applications

Joins a user to a job and tracks the application lifecycle.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `job_id` | ObjectId | Ref: `jobs._id` |
| `status` | `ApplicationStatus` | State machine (see below) |
| `match_score` | float | 0.0–1.0, set by JobMatcher agent (not yet implemented -- JobMatcher agent does not exist yet) |
| `applied_at` | datetime | Set when status → `APPLIED` |
| `notes` | string | User's personal notes |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Application Status State Machine:**

```
SAVED ──────► APPLIED ────► INTERVIEWING ────► OFFERED ────► ACCEPTED
  │               │                │               │
  │               └────────────────┴───────────────┴────► REJECTED
  └───────────────────────────────────────────────────────► WITHDRAWN
```

ACCEPTED, REJECTED, and WITHDRAWN are terminal states. No transitions out.

**Indexes:**
- `user_id` — for `get_for_user()`
- `(user_id, job_id)` — unique, for `get_by_job_and_user()` (prevents duplicate applications)
- `(user_id, status)` — for kanban/status-filtered queries

---

### documents

AI-generated documents (cover letters, tailored resumes, outreach messages) attached to applications.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `application_id` | ObjectId | Ref: `applications._id` |
| `doc_type` | `DocumentType` | `cover_letter`, `tailored_resume`, `outreach_message` |
| `version` | int | Auto-incremented per (application, doc_type) |
| `content` | string | Final approved content |
| `is_approved` | bool | Default: `false` |
| `thread_id` | string | LangGraph checkpoint ID for HITL resume |
| `resume_id` | ObjectId | Nullable — which resume was used to generate this |
| `feedback` | string | User's revision feedback |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Notes on `thread_id`:**
- Generated as `uuid4()` when the document is first created (`POST /cover-letter`)
- Stored here so all subsequent API calls (stream, review, re-stream) can locate the LangGraph checkpoint
- Format: `550e8400-e29b-41d4-a716-446655440000`

**Indexes:**
- `application_doctype_idx`: `(application_id, doc_type)` — for `get_for_application()` and `get_latest()`
- `application_doctype_version_uidx`: `(application_id, doc_type, version)` — **unique** index enforcing atomic version assignment (prevents concurrent duplicate version numbers)
- `user_doctype_idx`: `(user_id, doc_type)` — for user-scope queries filtered by document type

---

### outreach_messages

LinkedIn/email outreach messages to contacts. Separate from `documents` because outreach has a recipient and delivery tracking.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `application_id` | ObjectId | Ref: `applications._id` |
| `contact_id` | ObjectId | Ref: `contacts._id` |
| `type` | `MessageType` | Tone/strategy for this recipient role |
| `content` | string | Approved message content |
| `is_approved` | bool | |
| `is_sent` | bool | Default: `false` |
| `sent_at` | datetime | Nullable |
| `created_at` | datetime | |
| `updated_at` | datetime | |

---

### interviews

Interview records with scheduling, type, and preparation data.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `application_id` | ObjectId | Ref: `applications._id` |
| `type` | `InterviewType` | `phone_screen`, `technical`, `behavioral`, `system_design`, `final` |
| `scheduled_at` | datetime | Nullable |
| `duration_minutes` | int | |
| `interviewer_name` | string | |
| `interviewer_title` | string | |
| `notes` | string | Pre-interview prep notes |
| `outcome_notes` | string | Post-interview notes |
| `questions_asked` | `list[string]` | Recorded after the interview |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Indexes:**
- `application_id` — for `get_for_application()`

---

### star_stories

Behavioral interview examples in STAR format. Indexed in Weaviate for semantic matching to interview questions.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `title` | string | e.g., "Led migration of payment system" |
| `situation` | string | Context and background |
| `task` | string | Your specific responsibility |
| `action` | string | What you did, how, why |
| `result` | string | Measurable outcomes |
| `tags` | `list[string]` | e.g., ["leadership", "backend", "migration"] |
| `created_at` | datetime | |
| `updated_at` | datetime | |

**Weaviate index:** The concatenation of all 4 STAR fields is embedded and stored in `STARStoryEmbedding` for semantic question matching.

---

### llm_usage

Cost and token tracking for every LLM call. Feeds the analytics endpoints.

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref: `users._id` |
| `agent` | string | Which agent made the call, e.g., `cover_letter_writer` |
| `task_type` | string | `cover_letter`, `data_extraction`, etc. |
| `provider` | string | `anthropic`, `openai`, `groq` |
| `model` | string | Full model ID, e.g., `claude-sonnet-4-5` |
| `input_tokens` | int | |
| `output_tokens` | int | |
| `cost_usd` | float | Calculated from per-token pricing table |
| `latency_ms` | int | |
| `created_at` | datetime | |

**Indexes:**
- `(user_id, created_at)` — for per-user period queries
- `(user_id, agent)` — for per-agent analytics

---

### `refresh_tokens`

Server-side refresh token records for token rotation and reuse detection (RFC 6749 Section 10.4).

| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | Auto-generated |
| `user_id` | ObjectId | Owner of the token (indexed) |
| `token_jti` | string | JWT ID claim — unique identifier (unique index) |
| `family_id` | string | Groups tokens from same login session (indexed) |
| `is_revoked` | boolean | Set atomically via CAS on rotation |
| `expires_at` | datetime | Mirrors JWT exp claim |
| `created_at` | datetime | Auto-set on insert |
| `updated_at` | datetime | Auto-set on save |
| `schema_version` | int | Default: 1 |

**Indexes:**

- `token_jti` (unique) — fast lookup for CAS revocation
- `user_id` — per-user token queries
- `family_id` — family-wide revocation on reuse detection

---

## Weaviate Collections

All 4 collections use **multi-tenancy** — each user's data is isolated in a tenant identified by `user_id`. This provides data isolation without multiple Weaviate instances.

**Common properties (all collections):**

| Property | Type | Notes |
|----------|------|-------|
| `user_id` | string | Tenant identifier |
| `created_at` | date | |

**Embedding model:** `BAAI/bge-small-en-v1.5` — 384-dimensional vectors, cosine distance, loaded locally (no API cost).

---

### ResumeChunk

Chunked resume sections for semantic job matching and cover letter context retrieval.

| Property | Type | Notes |
|----------|------|-------|
| `resume_id` | string | Ref: MongoDB `resumes._id` |
| `chunk_type` | string | Section name: `work_experience`, `skills`, `education`, etc. |
| `content` | string | Raw text of this section |
| `metadata` | object | `{"user_id": "...", "resume_id": "..."}` |

**Used by:** `cover_letter_writer` memory recipe to find relevant resume sections.

---

### JobEmbedding

Job descriptions for similarity search — finding jobs similar to ones the user liked.

| Property | Type | Notes |
|----------|------|-------|
| `job_id` | string | Ref: MongoDB `jobs._id` |
| `title` | string | Job title |
| `description_summary` | string | First 500 chars of description |
| `chunk_type` | string | Section type if chunked |

**Used by:** JobMatcher agent to find semantically similar jobs. (Not yet implemented)

---

### CoverLetterEmbedding

Past approved cover letters for reuse and style consistency.

| Property | Type | Notes |
|----------|------|-------|
| `doc_id` | string | Ref: MongoDB `documents._id` |
| `content_summary` | string | First 500 chars |
| `company` | string | Target company name |
| `role` | string | Target role title |

**Used by:** `cover_letter_writer` memory recipe to retrieve past letters for style reference.

---

### STARStoryEmbedding

Behavioral stories for semantic matching to interview questions.

| Property | Type | Notes |
|----------|------|-------|
| `story_id` | string | Ref: MongoDB `star_stories._id` |
| `story_summary` | string | Concatenated STAR text |
| `tags` | `list[string]` | Story tags for filtering |

**Used by:** `star_helper` and `mock_interviewer` agents to find relevant stories for a given question.

---

## Enumerations

All enums use Python's `StrEnum` (Python 3.11+) — stored as readable strings in MongoDB.

### ApplicationStatus

```
SAVED         → Job bookmarked, not yet applied
APPLIED       → Application submitted
INTERVIEWING  → Interview process underway
OFFERED       → Offer received
ACCEPTED      → Offer accepted (terminal)
REJECTED      → Application rejected (terminal)
WITHDRAWN     → User withdrew (terminal)
```

### DocumentType

```
COVER_LETTER       → AI-generated cover letter
TAILORED_RESUME    → Resume tailored to specific JD
OUTREACH_MESSAGE   → LinkedIn/email outreach draft
```

### MessageType

```
RECRUITER   → Formal, qualifications-focused
ENGINEER    → Technical, project/stack-focused
MANAGER     → Strategic, impact/leadership-focused
GENERIC     → Balanced, for unknown recipient roles
```

### InterviewType

```
PHONE_SCREEN   → Initial recruiter screen
TECHNICAL      → Coding challenge / technical questions
BEHAVIORAL     → STAR-format behavioral interview
SYSTEM_DESIGN  → Architecture / design interview
FINAL          → Final round / executive interview
```

### RemotePreference

```
REMOTE         → Fully remote only
HYBRID         → Mix of remote and onsite
ONSITE         → Fully onsite only
NO_PREFERENCE  → Any arrangement acceptable
```

---

## Collection Relationships

```
users (1)
  │
  ├──(1:1)── profiles
  │
  ├──(1:N)── resumes
  │              └──(1:1)── ResumeChunk[] (Weaviate, per section)
  │
  ├──(1:N)── jobs
  │              ├──(N:1)── companies
  │              │               └──(1:N)── contacts
  │              └──(1:1)── JobEmbedding (Weaviate)
  │
  ├──(1:N)── applications
  │              ├──(N:1)── jobs
  │              │
  │              ├──(1:N)── documents
  │              │               ├──(1:1)── CoverLetterEmbedding (Weaviate, if cover letter)
  │              │               └──(LangGraph checkpoint stored in MongoDB
  │              │                  via thread_id key)
  │              │
  │              ├──(1:N)── outreach_messages
  │              │               └──(N:1)── contacts
  │              │
  │              └──(1:N)── interviews
  │
  ├──(1:N)── star_stories
  │               └──(1:1)── STARStoryEmbedding (Weaviate)
  │
  └──(1:N)── llm_usage
```

### Cascade Deletion: DELETE /jobs/{id}

Deleting a job triggers cascade deletion of all associated data:

```text
Job ──► Application (via get_by_job_and_user)
            │
            ├──► DocumentRecords (delete_for_application)
            │       └──► CoverLetterEmbeddings (Weaviate, non-blocking)
            ├──► OutreachMessages (delete_many by application_id)
            ├──► Interviews (delete_many by application_id)
            └──► Application itself (delete)
Job ──► JobEmbeddings (Weaviate, non-blocking)
Job ──► Job itself (delete)
```

Weaviate deletions are non-blocking: failures are logged as warnings and never
cause the HTTP request to fail.
