"""
Job discovery and management routes (Stage 2: Discover Jobs).

Design decisions
----------------
Why Jobs and Applications are created together:
    Adding a job to the system always creates an Application record with
    status=SAVED. This is the core UX: "save a job" = "add it to your
    pipeline." A Job without an Application would be an orphan.

    The response includes both job_id and application_id so the client
    can navigate to either resource immediately.

Why Job has no user_id (ownership via Application):
    The original data model uses Application as the join table between
    User and Job. Listing "my jobs" means querying Applications for the
    user and loading the referenced Jobs. This allows future multi-user
    scenarios where multiple users can track the same job listing.

    For performance, we do two DB queries: one for Applications, one
    batch lookup for Jobs (find_by_ids) — O(2) not O(N+1).

Why company is created lazily:
    When adding a job manually, the user provides company_name. The Company
    document (with culture notes, research, contacts) is created later by
    the CompanyResearcher agent. Until then, company_name is stored directly
    on the Job for display purposes.
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel

from src.api.dependencies import (
    build_indexing_service,
    get_application_repository,
    get_company_repository,
    get_contact_repository,
    get_current_user,
    get_document_repository,
    get_interview_repository,
    get_job_repository,
    get_outreach_message_repository,
)
from src.core.exceptions import AuthorizationError, NotFoundError
from src.db.documents.application import Application
from src.db.documents.company import Company
from src.db.documents.contact import Contact
from src.db.documents.enums import ApplicationStatus, DocumentType
from src.db.documents.job import Job, JobRequirements
from src.db.documents.user import User
from src.repositories.application_repository import ApplicationRepository
from src.repositories.base import BaseRepository
from src.repositories.company_repository import CompanyRepository
from src.repositories.contact_repository import ContactRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.job_repository import JobRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/jobs", tags=["jobs"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateJobRequest(BaseModel):
    title: str
    company_name: str
    description: str = ""
    location: str = ""
    remote: bool = False
    url: str = ""
    source: str = "manual"
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience_years: int | None = None


class JobSummary(BaseModel):
    job_id: str
    application_id: str
    title: str
    company_name: str
    location: str
    remote: bool
    url: str
    status: str
    created_at: str | None


class JobDetail(JobSummary):
    description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_years: int | None
    applied_at: str | None


class CreateContactRequest(BaseModel):
    name: str
    role: str = ""
    title: str = ""
    email: str = ""
    linkedin_url: str = ""
    notes: str = ""


class UpdateContactRequest(BaseModel):
    role: str | None = None
    title: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    contacted: bool | None = None


class ContactResponse(BaseModel):
    id: str
    company_id: str | None
    name: str
    role: str
    title: str
    email: str
    linkedin_url: str
    notes: str
    contacted: bool
    created_at: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _job_summary(job: Job, application: Application) -> JobSummary:
    return JobSummary(
        job_id=str(job.id),
        application_id=str(application.id),
        title=job.title,
        company_name=job.company_name,
        location=job.location,
        remote=job.remote,
        url=job.url,
        status=application.status,
        created_at=application.created_at.isoformat() if application.created_at else None,
    )


def _contact_to_response(c: Contact) -> ContactResponse:
    return ContactResponse(
        id=str(c.id),
        company_id=str(c.company_id) if c.company_id else None,
        name=c.name,
        role=c.role,
        title=c.title,
        email=c.email,
        linkedin_url=c.linkedin_url,
        notes=c.notes,
        contacted=c.contacted,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/manual", status_code=201)
async def add_job_manually(
    body: CreateJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
) -> dict:
    """
    Add a job manually. Creates both a Job document and an Application(status=SAVED).

    After the MongoDB writes succeed, queues a background task to index the
    job description into Weaviate for semantic search. Indexing failure does
    not affect the job save.
    """
    job = Job(
        title=body.title,
        company_name=body.company_name,
        description=body.description,
        location=body.location,
        remote=body.remote,
        url=body.url,
        source=body.source,
        requirements=JobRequirements(
            required_skills=body.required_skills,
            preferred_skills=body.preferred_skills,
            experience_years=body.experience_years,
        ),
    )
    job = await job_repo.create(job)

    application = Application(
        user_id=current_user.id,
        job_id=job.id,
        status=ApplicationStatus.SAVED,
    )
    application = await app_repo.create(application)

    # Queue job indexing into Weaviate (post-response, non-blocking)
    if job.description and job.description.strip():
        background_tasks.add_task(
            _index_job_background, str(job.id), str(current_user.id)
        )
    else:
        logger.info(
            "job_indexing_skipped_no_description",
            job_id=str(job.id),
            user_id=str(current_user.id),
        )

    logger.info(
        "job_added_manually",
        user_id=str(current_user.id),
        job_id=str(job.id),
    )
    return {
        "job_id": str(job.id),
        "application_id": str(application.id),
        "status": "saved",
    }


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    status: ApplicationStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> list[JobSummary]:
    """
    List jobs for the current user. Optionally filter by application status.
    Uses two queries (Applications -> Jobs) to avoid N+1.
    """
    applications = await app_repo.get_for_user(
        current_user.id, skip=skip, limit=limit, status=status
    )
    if not applications:
        return []

    job_ids = [app.job_id for app in applications]
    jobs = await job_repo.find_by_ids(job_ids)
    job_map = {str(j.id): j for j in jobs}

    result = []
    for app in applications:
        job = job_map.get(str(app.job_id))
        if job:
            result.append(_job_summary(job, app))
    return result


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
) -> JobDetail:
    """Get a single job with full details. Verifies ownership via Application."""
    job = await job_repo.get_by_id(PydanticObjectId(job_id))
    if not job:
        raise NotFoundError("Job", job_id)

    application = await app_repo.get_by_job_and_user(job.id, current_user.id)
    if not application:
        raise AuthorizationError("Not authorized to access this job")

    return JobDetail(
        **_job_summary(job, application).model_dump(),
        description=job.description,
        required_skills=job.requirements.required_skills,
        preferred_skills=job.requirements.preferred_skills,
        experience_years=job.requirements.experience_years,
        applied_at=application.applied_at.isoformat() if application.applied_at else None,
    )


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
    outreach_repo: BaseRepository = Depends(get_outreach_message_repository),
    interview_repo: BaseRepository = Depends(get_interview_repository),
) -> None:
    """Delete a job and cascade-delete all associated data.

    Deletes: DocumentRecords, OutreachMessages, Interviews, the Application,
    Weaviate embeddings (JobEmbedding + CoverLetterEmbedding), and the Job.
    Weaviate failures are non-blocking (logged as warnings).
    """
    job = await job_repo.get_by_id(PydanticObjectId(job_id))
    if not job:
        raise NotFoundError("Job", job_id)

    application = await app_repo.get_by_job_and_user(job.id, current_user.id)
    if not application:
        raise AuthorizationError("Not authorized to delete this job")

    user_id = str(current_user.id)

    # -- Cascade: delete children of the application -----------------------
    indexing_service = build_indexing_service()

    # Get cover letter doc IDs for Weaviate cleanup BEFORE deleting from MongoDB
    docs = await doc_repo.get_for_application(application.id)
    cover_letter_doc_ids = [
        str(d.id) for d in docs if d.doc_type == DocumentType.COVER_LETTER
    ]

    # Weaviate: delete CoverLetterEmbeddings (non-blocking)
    if cover_letter_doc_ids:
        try:
            await indexing_service.delete_cover_letter_embeddings_for_docs(
                cover_letter_doc_ids, user_id
            )
        except Exception:
            logger.warning(
                "cascade_cover_letter_embedding_delete_failed",
                job_id=job_id,
                user_id=user_id,
            )

    # MongoDB: delete documents, outreach messages, interviews
    docs_deleted = await doc_repo.delete_for_application(application.id)
    outreach_deleted = await outreach_repo.delete_many(
        {"application_id": application.id}
    )
    interviews_deleted = await interview_repo.delete_many(
        {"application_id": application.id}
    )

    await app_repo.delete(application.id)

    # -- Weaviate: delete JobEmbedding (non-blocking) ----------------------
    try:
        await indexing_service.delete_job_embeddings(str(job.id), user_id)
    except Exception:
        logger.warning(
            "cascade_job_embedding_delete_failed",
            job_id=job_id,
            user_id=user_id,
        )

    # -- Delete the job itself ---------------------------------------------
    await job_repo.delete(PydanticObjectId(job_id))
    logger.info(
        "job_cascade_deleted",
        user_id=user_id,
        job_id=job_id,
        docs_deleted=docs_deleted,
        outreach_deleted=outreach_deleted,
        interviews_deleted=interviews_deleted,
    )


@router.get("/{job_id}/contacts", response_model=list[ContactResponse])
async def list_contacts(
    job_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    contact_repo: ContactRepository = Depends(get_contact_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
) -> list[ContactResponse]:
    """List contacts for the company associated with this job."""
    job = await job_repo.get_by_id(PydanticObjectId(job_id))
    if not job:
        raise NotFoundError("Job", job_id)
    if not await app_repo.get_by_job_and_user(job.id, current_user.id):
        raise AuthorizationError("Not authorized")

    if not job.company_id:
        return []

    contacts = await contact_repo.get_for_company(job.company_id, skip=skip, limit=limit)
    return [_contact_to_response(c) for c in contacts]


@router.post("/{job_id}/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(
    job_id: str,
    body: CreateContactRequest,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    contact_repo: ContactRepository = Depends(get_contact_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
) -> ContactResponse:
    """Manually add a contact for the job's company."""
    job = await job_repo.get_by_id(PydanticObjectId(job_id))
    if not job:
        raise NotFoundError("Job", job_id)
    if not await app_repo.get_by_job_and_user(job.id, current_user.id):
        raise AuthorizationError("Not authorized")

    # Create or get Company document if needed
    company_id = job.company_id
    if not company_id and job.company_name:
        company = await company_repo.get_by_name(job.company_name)
        if not company:
            company = await company_repo.create(Company(name=job.company_name))
        company_id = company.id
        await job_repo.update(job.id, {"company_id": company_id})

    contact = Contact(
        company_id=company_id,
        name=body.name,
        role=body.role,
        title=body.title,
        email=body.email,
        linkedin_url=body.linkedin_url,
        notes=body.notes,
    )
    contact = await contact_repo.create(contact)
    logger.info(
        "contact_created",
        user_id=str(current_user.id),
        job_id=job_id,
        contact_id=str(contact.id),
    )
    return _contact_to_response(contact)


@router.patch("/{job_id}/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    job_id: str,
    contact_id: str,
    body: UpdateContactRequest,
    current_user: User = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
    app_repo: ApplicationRepository = Depends(get_application_repository),
    contact_repo: ContactRepository = Depends(get_contact_repository),
) -> ContactResponse:
    """Update a contact's details or mark as contacted."""
    job = await job_repo.get_by_id(PydanticObjectId(job_id))
    if not job:
        raise NotFoundError("Job", job_id)
    if not await app_repo.get_by_job_and_user(job.id, current_user.id):
        raise AuthorizationError("Not authorized")

    contact = await contact_repo.get_by_id(PydanticObjectId(contact_id))
    if not contact:
        raise NotFoundError("Contact", contact_id)

    update_data: dict = {}
    for field in ["role", "title", "email", "linkedin_url", "notes", "contacted"]:
        val = getattr(body, field)
        if val is not None:
            update_data[field] = val
    if update_data:
        updated = await contact_repo.update(PydanticObjectId(contact_id), update_data)
        contact = updated or contact

    return _contact_to_response(contact)


# ---------------------------------------------------------------------------
# Background helpers
# ---------------------------------------------------------------------------


async def _index_job_background(job_id: str, user_id: str) -> None:
    """
    Background task: index a job description into Weaviate.

    Calls IndexingService.index_job() to chunk, embed, and store the job
    description for semantic search. Errors are caught and logged -- they
    must not crash the background task or affect the job save.
    """
    try:
        service = build_indexing_service()
        await service.index_job(job_id, user_id)
        logger.info(
            "job_indexing_completed",
            job_id=job_id,
            user_id=user_id,
        )
    except Exception:
        logger.exception(
            "job_indexing_failed",
            job_id=job_id,
            user_id=user_id,
        )
