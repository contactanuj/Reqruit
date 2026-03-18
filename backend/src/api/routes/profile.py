"""
Profile and resume management routes (Stage 1: Profile Setup).

Design decisions
----------------
Why GET /profile auto-creates a profile:
    First-time users have no profile document. Rather than requiring a
    separate "create profile" call, the GET auto-creates an empty profile.
    This reduces client complexity — the frontend can always GET /profile
    without checking if one exists first.

Why PATCH (not PUT) for profile updates:
    Users update individual sections of their profile over time (skills one
    day, preferences another). PATCH allows partial updates with $set
    semantics — only the provided fields are changed. PUT would require
    sending the entire profile on every update, risking data loss.

Why resume upload returns 202 (not 201):
    Resume parsing is asynchronous — it requires an LLM call to extract
    structured data. The route immediately creates the Resume document with
    raw_text, returns 202 Accepted, and parsing happens in a BackgroundTask.
    The client polls /parse-status to know when parsing is complete.

Why is_master logic on PATCH:
    Only one resume can be the master. Setting is_master=True on one resume
    must unset it on all others. This is enforced in the route by calling
    unset_master_for_user() before setting the new master, ensuring the
    invariant holds even under concurrent requests.
"""

import io

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from pydantic import BaseModel

from src.api.dependencies import (
    build_indexing_service,
    get_current_user,
    get_profile_repository,
    get_resume_repository,
)
from src.core.exceptions import (
    AuthorizationError,
    BusinessValidationError,
    NotFoundError,
)
from src.db.documents.profile import Profile
from src.db.documents.resume import Resume
from src.db.documents.user import User
from src.repositories.profile_repository import ProfileRepository
from src.repositories.resume_repository import ResumeRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/profile", tags=["profile"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class PreferencesBody(BaseModel):
    preferred_locations: list[str] | None = None
    remote_preference: str | None = None
    willing_to_relocate: bool | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] | None = None
    target_roles: list[str] | None = None
    years_of_experience: int | None = None
    preferences: PreferencesBody | None = None


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    headline: str
    summary: str
    skills: list[str]
    target_roles: list[str]
    years_of_experience: int | None
    updated_at: str | None


class ResumeListItem(BaseModel):
    id: str
    title: str
    file_name: str
    version: int
    is_master: bool
    parse_status: str  # "pending" | "parsed"
    created_at: str | None


class ResumeDetail(ResumeListItem):
    raw_text: str
    parsed_data: dict | None


class UpdateResumeRequest(BaseModel):
    title: str | None = None
    is_master: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resume_parse_status(resume: Resume) -> str:
    # Transition period: existing resumes without parse_status field
    # default to "pending", but if parsed_data is populated, they're completed
    if resume.parse_status == "pending" and resume.parsed_data is not None:
        return "completed"
    return resume.parse_status


def _profile_to_response(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile.id),
        full_name=profile.full_name,
        headline=profile.headline,
        summary=profile.summary,
        skills=profile.skills,
        target_roles=profile.target_roles,
        years_of_experience=profile.years_of_experience,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )


def _resume_to_list_item(resume: Resume) -> ResumeListItem:
    return ResumeListItem(
        id=str(resume.id),
        title=resume.title,
        file_name=resume.file_name,
        version=resume.version,
        is_master=resume.is_master,
        parse_status=_resume_parse_status(resume),
        created_at=resume.created_at.isoformat() if resume.created_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    """Get the current user's profile. Auto-creates an empty profile on first call."""
    profile = await profile_repo.get_or_create(current_user.id)
    logger.info("profile_fetched", user_id=str(current_user.id))
    return _profile_to_response(profile)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileResponse:
    """Update profile fields. Only provided fields are changed (PATCH semantics)."""
    profile = await profile_repo.get_or_create(current_user.id)

    update_data: dict = {}
    if body.full_name is not None:
        update_data["full_name"] = body.full_name
    if body.headline is not None:
        update_data["headline"] = body.headline
    if body.summary is not None:
        update_data["summary"] = body.summary
    if body.skills is not None:
        update_data["skills"] = body.skills
    if body.target_roles is not None:
        update_data["target_roles"] = body.target_roles
    if body.years_of_experience is not None:
        update_data["years_of_experience"] = body.years_of_experience
    if body.preferences is not None:
        prefs = profile.preferences
        if body.preferences.preferred_locations is not None:
            prefs.preferred_locations = body.preferences.preferred_locations
        if body.preferences.remote_preference is not None:
            prefs.remote_preference = body.preferences.remote_preference
        if body.preferences.willing_to_relocate is not None:
            prefs.willing_to_relocate = body.preferences.willing_to_relocate
        update_data["preferences"] = prefs.model_dump()

    if update_data:
        updated = await profile_repo.update(profile.id, update_data)
        profile = updated or profile

    logger.info(
        "profile_updated",
        user_id=str(current_user.id),
        fields=list(update_data.keys()),
    )
    return _profile_to_response(profile)


@router.get("/resumes", response_model=list[ResumeListItem])
async def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> list[ResumeListItem]:
    """List all resumes for the current user, sorted newest first."""
    resumes = await resume_repo.get_all_for_user(current_user.id, skip=skip, limit=limit)
    return [_resume_to_list_item(r) for r in resumes]


@router.post("/resumes/upload", status_code=202)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Query(""),
    is_master: bool = Query(False),
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> dict:
    """
    Upload a PDF or DOCX resume. Returns 202 immediately; parsing is async.

    The file's raw text is extracted synchronously (fast). LLM-based
    structured parsing happens in a background task.
    """
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types:
        raise BusinessValidationError(
            "Only PDF and DOCX files are supported", "INVALID_FILE_TYPE"
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise BusinessValidationError("File size exceeds 10MB limit", "FILE_TOO_LARGE")

    raw_text = _extract_text(content, file.content_type)

    count = await resume_repo.count_for_user(current_user.id)

    if is_master:
        await resume_repo.unset_master_for_user(current_user.id)

    resume = Resume(
        user_id=current_user.id,
        title=title or (file.filename or "Resume"),
        raw_text=raw_text,
        file_name=file.filename or "resume",
        version=count + 1,
        is_master=is_master,
    )
    resume = await resume_repo.create(resume)

    background_tasks.add_task(
        _parse_resume_background, str(resume.id), raw_text, str(current_user.id)
    )

    logger.info(
        "resume_uploaded",
        user_id=str(current_user.id),
        resume_id=str(resume.id),
        is_master=is_master,
    )
    return {"resume_id": str(resume.id), "status": "parsing", "version": resume.version}


@router.get("/resumes/{resume_id}", response_model=ResumeDetail)
async def get_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> ResumeDetail:
    """Get a single resume with full content."""
    resume = await resume_repo.get_by_id(PydanticObjectId(resume_id))
    if not resume:
        raise NotFoundError("Resume", resume_id)
    if resume.user_id != current_user.id:
        raise AuthorizationError("Not authorized to access this resume")

    return ResumeDetail(
        **_resume_to_list_item(resume).model_dump(),
        raw_text=resume.raw_text,
        parsed_data=resume.parsed_data.model_dump() if resume.parsed_data else None,
    )


@router.patch("/resumes/{resume_id}", response_model=ResumeListItem)
async def update_resume(
    resume_id: str,
    body: UpdateResumeRequest,
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> ResumeListItem:
    """Update resume title or master status."""
    resume = await resume_repo.get_by_id(PydanticObjectId(resume_id))
    if not resume:
        raise NotFoundError("Resume", resume_id)
    if resume.user_id != current_user.id:
        raise AuthorizationError("Not authorized to update this resume")

    update_data: dict = {}
    if body.title is not None:
        update_data["title"] = body.title
    if body.is_master is True:
        await resume_repo.unset_master_for_user(current_user.id)
        update_data["is_master"] = True
    elif body.is_master is False:
        update_data["is_master"] = False

    if update_data:
        updated = await resume_repo.update(PydanticObjectId(resume_id), update_data)
        resume = updated or resume

    logger.info(
        "resume_updated",
        user_id=str(current_user.id),
        resume_id=resume_id,
    )
    return _resume_to_list_item(resume)


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> None:
    """Delete a resume."""
    resume = await resume_repo.get_by_id(PydanticObjectId(resume_id))
    if not resume:
        raise NotFoundError("Resume", resume_id)
    if resume.user_id != current_user.id:
        raise AuthorizationError("Not authorized to delete this resume")

    await resume_repo.delete(PydanticObjectId(resume_id))
    logger.info("resume_deleted", user_id=str(current_user.id), resume_id=resume_id)


@router.get("/resumes/{resume_id}/parse-status")
async def get_parse_status(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> dict:
    """Poll the parse status of an uploaded resume."""
    resume = await resume_repo.get_by_id(PydanticObjectId(resume_id))
    if not resume:
        raise NotFoundError("Resume", resume_id)
    if resume.user_id != current_user.id:
        raise AuthorizationError("Not authorized")
    return {"resume_id": resume_id, "status": _resume_parse_status(resume)}


@router.post("/resumes/{resume_id}/reparse", status_code=202)
async def reparse_resume(
    resume_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> dict:
    """Retry parsing a failed resume without re-uploading."""
    resume = await resume_repo.get_by_user_and_id(
        current_user.id, PydanticObjectId(resume_id)
    )
    if not resume:
        raise NotFoundError("Resume", resume_id)

    if resume.parse_status != "failed":
        raise BusinessValidationError(
            "Resume can only be re-parsed when parse status is 'failed'",
            "INVALID_STATUS_TRANSITION",
        )

    await resume_repo.update(
        PydanticObjectId(resume_id),
        {"parse_status": "pending", "parsed_data": None},
    )
    background_tasks.add_task(
        _parse_resume_background, str(resume.id), resume.raw_text, str(current_user.id)
    )

    logger.info(
        "resume_reparse_queued",
        user_id=str(current_user.id),
        resume_id=resume_id,
    )
    return {"resume_id": resume_id, "status": "reparse_queued"}


# ---------------------------------------------------------------------------
# Background helpers
# ---------------------------------------------------------------------------


async def _parse_resume_background(resume_id: str, raw_text: str, user_id: str) -> None:
    """
    Background task: parse resume and index into Weaviate.

    Parsing is currently a stub (ResumeParser agent not yet built).
    Indexing calls IndexingService.index_resume() to chunk, embed, and
    store the raw_text in Weaviate for RAG retrieval.

    Status transitions: pending -> processing -> completed (or failed).
    """
    resume_repo = ResumeRepository()
    try:
        await resume_repo.update(
            PydanticObjectId(resume_id), {"parse_status": "processing"}
        )
        logger.info("resume_parse_started", resume_id=resume_id, text_length=len(raw_text))

        # TODO: implement when ResumeParser agent exists
        logger.info("resume_parse_skipped_no_agent", resume_id=resume_id)

        await resume_repo.update(
            PydanticObjectId(resume_id), {"parse_status": "skipped"}
        )

        # Index resume into Weaviate for RAG retrieval
        if raw_text and raw_text.strip():
            try:
                service = build_indexing_service()
                chunk_count = await service.index_resume(resume_id, user_id)
                logger.info(
                    "resume_indexing_completed",
                    resume_id=resume_id,
                    user_id=user_id,
                    chunk_count=chunk_count,
                )
            except Exception:
                logger.exception(
                    "resume_indexing_failed",
                    resume_id=resume_id,
                    user_id=user_id,
                )
        else:
            logger.info("resume_indexing_skipped_no_text", resume_id=resume_id)
    except Exception:
        await resume_repo.update(
            PydanticObjectId(resume_id), {"parse_status": "failed"}
        )
        logger.exception(
            "resume_parse_failed", resume_id=resume_id, user_id=user_id
        )


def _extract_text(content: bytes, content_type: str) -> str:
    """Extract raw text from PDF or DOCX bytes."""
    try:
        if content_type == "application/pdf":
            try:
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(content))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                return ""
        else:
            try:
                import docx

                doc = docx.Document(io.BytesIO(content))
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return ""
    except Exception:
        return ""
