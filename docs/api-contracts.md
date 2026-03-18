# Reqruit — API Contracts

> Complete endpoint inventory generated from deep source code scan.

**Generated**: 2026-03-14 | **Base URL**: `http://localhost:8000`

All authenticated endpoints require `Authorization: Bearer <access_token>`.

---

## System Endpoints (No Auth)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | 200 | Liveness check (app name, version, environment) |
| GET | `/health/ready` | 200 | Readiness check (MongoDB + Weaviate status) |

---

## Auth (`/auth`) — No Auth Required (except /me)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/auth/register` | 201 | Register new user → returns tokens |
| POST | `/auth/login` | 200 | Login → returns tokens |
| POST | `/auth/refresh` | 200 | Rotate refresh token → new token pair |
| GET | `/auth/me` | 200 | Get current user (requires Bearer) |

**Schemas**:
- Register: `{email, password}` → `{access_token, refresh_token, token_type}`
- Login: `{email, password}` → `{access_token, refresh_token, token_type}`
- Refresh: `{refresh_token}` → `{access_token, refresh_token, token_type}`
- Me: → `{id, email, is_active}`

**Security**: Generic error on login failure (prevents account enumeration). Refresh token rotation with family tracking (reuse = theft detection).

---

## Profile (`/profile`) — Auth Required

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/profile` | 200 | Get user profile (auto-creates if missing) |
| PATCH | `/profile` | 200 | Update profile fields |
| GET | `/profile/resumes` | 200 | List user's resumes (paginated) |
| POST | `/profile/resumes/upload` | 202 | Upload resume (async parsing) |
| GET | `/profile/resumes/{resume_id}` | 200 | Get resume detail (incl. parsed data) |
| PATCH | `/profile/resumes/{resume_id}` | 200 | Update resume metadata |
| DELETE | `/profile/resumes/{resume_id}` | 204 | Delete resume |
| GET | `/profile/resumes/{resume_id}/parse-status` | 200 | Check parsing progress |
| POST | `/profile/resumes/{resume_id}/reparse` | 202 | Re-trigger parsing (failed only) |

**Schemas**:
- UpdateProfile: `{full_name, headline, summary, skills[], target_roles[], years_of_experience, preferences}`
- ResumeUpload: multipart/form-data (`file`, `title`, `is_master`)
- Constraints: PDF/DOCX only, max 10MB, one master resume per user

---

## Jobs (`/jobs`) — Auth Required

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/jobs/manual` | 201 | Add job manually → creates Job + Application(SAVED) |
| GET | `/jobs` | 200 | List jobs (filterable by status, paginated) |
| GET | `/jobs/{job_id}` | 200 | Get job detail |
| DELETE | `/jobs/{job_id}` | 204 | Delete job (cascade: docs, outreach, interviews, application) |
| GET | `/jobs/{job_id}/contacts` | 200 | List contacts for job's company |
| POST | `/jobs/{job_id}/contacts` | 201 | Add contact (auto-creates Company if needed) |
| PATCH | `/jobs/{job_id}/contacts/{contact_id}` | 200 | Update contact |

**Schemas**:
- CreateJob: `{title, company_name, description, location, remote, url, source, required_skills[], preferred_skills[], experience_years}`
- CreateContact: `{name, role, title, email, linkedin_url, notes}`

---

## Apply (`/apply`) — Auth Required

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/apply/applications/{app_id}/documents` | 200 | List documents for application |
| POST | `/apply/applications/{app_id}/cover-letter` | 202 | Start cover letter generation |
| GET | `/apply/applications/{app_id}/cover-letter/stream` | 200 | SSE stream of generation output |
| POST | `/apply/applications/{app_id}/cover-letter/review` | 200 | Approve or request revision (HITL) |

**Flow**:
1. `POST /cover-letter` → Creates DocumentRecord, starts LangGraph workflow → returns `{thread_id}`
2. `GET /cover-letter/stream?thread_id=X` → Opens SSE connection, streams tokens
3. `POST /cover-letter/review` → `{thread_id, action: "approve"|"revise", feedback}` → resumes workflow

**Features**: Rate limiting (per-user LLM budget), duplicate detection, SSE with checkpoint reconnect, revision loop.

---

## Track (`/track`) — Auth Required

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/track/kanban` | 200 | All active apps grouped by status (saved/applied/interviewing/offered) |
| GET | `/track/applications` | 200 | List applications (filterable by status, paginated) |
| GET | `/track/applications/archive` | 200 | Archived apps (accepted/rejected/withdrawn) |
| PATCH | `/track/applications/{app_id}/status` | 200 | Transition status (validated) |
| PATCH | `/track/applications/{app_id}/notes` | 200 | Update notes |

**Status Machine**:
- SAVED → {APPLIED, WITHDRAWN}
- APPLIED → {INTERVIEWING, REJECTED, WITHDRAWN}
- INTERVIEWING → {OFFERED, REJECTED, WITHDRAWN}
- OFFERED → {ACCEPTED, REJECTED, WITHDRAWN}
- Terminal: ACCEPTED, REJECTED, WITHDRAWN (no further transitions)

---

## Interviews (`/interviews`) — Auth Required

### Core CRUD

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/interviews` | 201 | Create interview for application |
| GET | `/interviews` | 200 | List interviews (filter by application_id) |
| GET | `/interviews/{id}` | 200 | Get interview detail |
| PATCH | `/interviews/{id}` | 200 | Update interview |
| DELETE | `/interviews/{id}` | 204 | Delete interview |

### STAR Stories

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/interviews/star-stories` | 201 | Create STAR story |
| GET | `/interviews/star-stories` | 200 | List STAR stories |
| GET | `/interviews/star-stories/{id}` | 200 | Get STAR story |
| PATCH | `/interviews/star-stories/{id}` | 200 | Update STAR story |
| DELETE | `/interviews/star-stories/{id}` | 204 | Delete STAR story |

### Question Generation (AI-powered)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/interviews/{id}/questions/generate` | 201 | Generate behavioral questions (BehavioralQuestionGenerator agent) |
| GET | `/interviews/{id}/questions` | 200 | Get generated questions |

### Mock Interview Sessions (AI-powered)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/interviews/{id}/mock-sessions` | 201 | Start mock session (idempotent) |
| GET | `/interviews/{id}/mock-sessions` | 200 | List sessions |
| GET | `/interviews/{id}/mock-sessions/{sid}` | 200 | Get session detail |
| POST | `/interviews/{id}/mock-sessions/{sid}/answer` | 200 | Submit answer (MockInterviewer agent evaluates) |
| POST | `/interviews/{id}/mock-sessions/{sid}/complete` | 200 | Complete session (MockInterviewSummarizer agent) |
| DELETE | `/interviews/{id}/mock-sessions/{sid}` | 204 | Delete session |

---

## Outreach (`/outreach`) — Auth Required

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/outreach/generate` | 201 | Generate outreach message (OutreachComposer agent) |
| GET | `/outreach` | 200 | List messages (filter by application_id, contact_id) |
| GET | `/outreach/{id}` | 200 | Get message |
| PATCH | `/outreach/{id}` | 200 | Edit message content |
| POST | `/outreach/{id}/send` | 200 | Mark as sent (prevents duplicates) |
| DELETE | `/outreach/{id}` | 204 | Delete message |

---

## Dependency Injection

14 repository providers + 1 auth dependency + 1 service factory + 1 workflow provider, all via FastAPI `Depends()`.

## Error Response Format

```json
{
  "error_code": "UPPER_SNAKE_CASE",
  "detail": "Human-readable message"
}
```

Key error codes: `AUTH_FAILED` (401), `AUTH_TOKEN_EXPIRED` (401), `NOT_FOUND` (404), `CONFLICT` (409), `VALIDATION_FAILED` (422), `INVALID_STATUS_TRANSITION` (422), `RATE_LIMITED` (429), `LLM_PROVIDER_ERROR` (502).

---

## Endpoint Count Summary

| Module | Endpoints |
|--------|-----------|
| System | 2 |
| Auth | 4 |
| Profile | 9 |
| Jobs | 7 |
| Apply | 4 |
| Track | 5 |
| Interviews | 16 |
| Outreach | 6 |
| **Total** | **53** |
