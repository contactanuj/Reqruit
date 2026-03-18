# Reqruit — Data Models (Deep Scan)

> Complete schema reference generated from deep source code analysis.

**Generated**: 2026-03-14 | **Scan Level**: Deep

---

## MongoDB Collections (14)

All collections inherit `TimestampedDocument` (created_at, updated_at via Beanie hooks, schema_version=1).

### users

| Field | Type | Notes |
|-------|------|-------|
| email | str | Unique index |
| hashed_password | str | bcrypt hash |
| is_active | bool | Default true (soft delete) |

### profiles

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | Unique index |
| full_name | str | |
| headline | str | |
| summary | str | |
| skills | list[str] | |
| target_roles | list[str] | |
| years_of_experience | int \| None | |
| preferences | UserPreferences | Embedded: target_salary (SalaryRange), preferred_locations[], remote_preference (enum), willing_to_relocate |

### resumes

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| title | str | |
| file_name | str | |
| raw_text | str | Full text extraction |
| parsed_data | ParsedResumeData \| None | Embedded: contact_info, work_experience[], education[], skills[], certifications[], languages[] |
| version | int | |
| is_master | bool | One master per user |
| parse_status | str | pending → processing → completed \| failed |
| **Index** | compound | (user_id, is_master) |

### jobs

| Field | Type | Notes |
|-------|------|-------|
| title | str | |
| company_id | PydanticObjectId \| None | Indexed |
| company_name | str | Denormalized for display |
| description | str | |
| requirements | JobRequirements | Embedded: required_skills[], preferred_skills[], experience_years |
| salary | SalaryRange \| None | Embedded: min_amount, max_amount, currency |
| location | str | |
| remote | bool | |
| url | str | |
| source | str | |
| **Index** | compound | (location, remote) |

### companies

| Field | Type | Notes |
|-------|------|-------|
| name | str | Unique index |
| domain | str | |
| website | str | |
| industry | str | |
| size | str | |
| culture_notes | str | |
| tech_stack | list[str] | |
| research | dict | Arbitrary research data |

### contacts

| Field | Type | Notes |
|-------|------|-------|
| company_id | PydanticObjectId | Indexed |
| name | str | |
| role | str | |
| title | str | |
| email | str | |
| linkedin_url | str | |
| notes | str | |
| contacted | bool | |
| contacted_at | datetime \| None | |

### applications

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| job_id | PydanticObjectId | Indexed |
| status | ApplicationStatus | Enum: SAVED, APPLIED, INTERVIEWING, OFFERED, ACCEPTED, REJECTED, WITHDRAWN |
| match_score | float \| None | AI-generated match score |
| match_reasoning | str | |
| applied_at | datetime \| None | Auto-set on APPLIED transition |
| notes | str | |
| **Index** | compound | (user_id, status) |

### documents

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| application_id | PydanticObjectId | Indexed |
| doc_type | DocumentType | Enum: COVER_LETTER, TAILORED_RESUME, OUTREACH_MESSAGE |
| content | str | Generated text |
| version | int | Atomic increment with retry |
| is_approved | bool | |
| feedback | str | User feedback for revision |
| thread_id | str | LangGraph workflow thread |
| resume_id | PydanticObjectId \| None | Which resume was used |
| **Index** | unique compound | (application_id, doc_type, version) |

### outreach_messages

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| application_id | PydanticObjectId | Indexed |
| contact_id | PydanticObjectId | |
| message_type | MessageType | Enum: RECRUITER, ENGINEER, MANAGER, GENERIC |
| content | str | |
| is_sent | bool | Prevents duplicate sends |
| sent_at | datetime \| None | |

### interviews

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| application_id | PydanticObjectId | |
| scheduled_at | datetime \| None | |
| interview_type | InterviewType | Enum: PHONE_SCREEN, TECHNICAL, BEHAVIORAL, SYSTEM_DESIGN, FINAL |
| company_name | str | Denormalized |
| role_title | str | Denormalized |
| interviewer_name | str | |
| notes | InterviewNotes | Embedded: key_points[], follow_up_items[] |
| questions | list[str] | Manual questions |
| generated_questions | list[GeneratedQuestion] | AI-generated: question + suggested_angle |
| preparation_notes | str | |
| **Index** | compound | (user_id, application_id) |

### star_stories

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| title | str | |
| situation | str | |
| task | str | |
| action | str | |
| result | str | |
| tags | list[str] | Indexed for search |

### llm_usage

| Field | Type | Notes |
|-------|------|-------|
| user_id | str | |
| agent | str | Which agent made the call |
| model | str | Actual model used |
| provider | str | anthropic / openai / groq |
| task_type | str | TaskType enum value |
| input_tokens | int | |
| output_tokens | int | |
| total_tokens | int | |
| cost_usd | float | Calculated from cost table |
| latency_ms | float | |
| **Index** | compound | (agent, model) |

### mock_sessions

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | |
| interview_id | PydanticObjectId | |
| status | MockSessionStatus | Enum: IN_PROGRESS, COMPLETED, ABANDONED |
| question_feedbacks | list[QuestionFeedback] | Embedded: question, user_answer, ai_feedback, score |
| current_question_index | int | |
| overall_feedback | str | AI-generated summary |
| overall_score | int | 0-100 |
| **Index** | compound | (user_id, interview_id) |

### refresh_tokens

| Field | Type | Notes |
|-------|------|-------|
| user_id | PydanticObjectId | Indexed |
| token_jti | str | Unique index (JWT ID) |
| family_id | str | Indexed (for family revocation) |
| is_revoked | bool | |
| expires_at | datetime | |

---

## Weaviate Collections (4)

All collections: HNSW index, cosine distance, 384-dim vectors (BGE-small-en-v1.5), multi-tenancy enabled.

### ResumeChunk

| Property | Type | Purpose |
|----------|------|---------|
| content | TEXT | Chunk text (section of resume) |
| chunk_type | TEXT | e.g., "work_experience", "skills", "fixed_size" |
| resume_id | TEXT | Source resume reference |
| user_id | TEXT | Owner reference |

### JobEmbedding

| Property | Type | Purpose |
|----------|------|---------|
| title | TEXT | Job title |
| description_summary | TEXT | Summarized job description |
| job_id | TEXT | Source job reference |
| user_id | TEXT | Owner reference |

### CoverLetterEmbedding

| Property | Type | Purpose |
|----------|------|---------|
| content_summary | TEXT | Summarized cover letter |
| company | TEXT | Target company |
| role | TEXT | Target role |
| doc_id | TEXT | Source document reference |

### STARStoryEmbedding

| Property | Type | Purpose |
|----------|------|---------|
| story_summary | TEXT | Concatenated STAR fields |
| tags | TEXT_ARRAY | Story tags |
| story_id | TEXT | Source story reference |

---

## Enums (6)

| Enum | Values |
|------|--------|
| ApplicationStatus | SAVED, APPLIED, INTERVIEWING, OFFERED, ACCEPTED, REJECTED, WITHDRAWN |
| DocumentType | COVER_LETTER, TAILORED_RESUME, OUTREACH_MESSAGE |
| MessageType | RECRUITER, ENGINEER, MANAGER, GENERIC |
| InterviewType | PHONE_SCREEN, TECHNICAL, BEHAVIORAL, SYSTEM_DESIGN, FINAL |
| MockSessionStatus | IN_PROGRESS, COMPLETED, ABANDONED |
| RemotePreference | REMOTE, HYBRID, ONSITE, NO_PREFERENCE |

---

## Repository Layer Summary

**MongoDB**: 16 concrete repositories + BaseRepository[T] generic
**Weaviate**: 4 concrete repositories + WeaviateRepository generic

Key patterns: owner-scoped queries, atomic versioning with retry, family-level token revocation, delete-before-reindex, two-query (avoid N+1).
