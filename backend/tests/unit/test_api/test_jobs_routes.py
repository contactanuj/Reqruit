"""
Unit tests for job discovery and management routes.

All DB and auth dependencies are overridden with mocks via client.app.
Tests verify route logic: status codes, response shapes, and error handling.

Why client.app (not `from src.api.main import app`):
    The `client` fixture creates a fresh FastAPI instance via create_app().
    The module-level `app` singleton is a separate object. Overrides must
    be applied to the same instance the client is sending requests to.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_document_repository,
    get_interview_repository,
    get_job_repository,
    get_outreach_message_repository,
)
from src.db.documents.application import Application
from src.db.documents.enums import ApplicationStatus
from src.db.documents.job import Job, JobRequirements

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_job(job_id: str = "111111111111111111111111"):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Senior Engineer"
    job.company_name = "Acme Corp"
    job.company_id = None
    job.description = "A great job"
    job.location = "Remote"
    job.remote = True
    job.url = "https://example.com/job"
    job.source = "manual"
    job.requirements = JobRequirements(required_skills=["python"], preferred_skills=[])
    job.created_at = None
    return job


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
    job_id: str = "111111111111111111111111",
):
    app = MagicMock(spec=Application)
    app.id = PydanticObjectId(app_id)
    app.user_id = PydanticObjectId(user_id)
    app.job_id = PydanticObjectId(job_id)
    app.status = ApplicationStatus.SAVED
    app.match_score = None
    app.match_reasoning = ""
    app.applied_at = None
    app.notes = ""
    app.created_at = None
    return app


# ---------------------------------------------------------------------------
# Tests: POST /jobs/manual
# ---------------------------------------------------------------------------


async def test_add_job_manually_creates_job_and_application(client: AsyncClient) -> None:
    """POST /jobs/manual should create both Job and Application, return 201."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_job = _make_job()
    fake_application = _make_application()

    mock_job_repo = AsyncMock()
    mock_job_repo.create.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.create.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.post(
            "/jobs/manual",
            json={"title": "Senior Engineer", "company_name": "Acme Corp"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "application_id" in data
        assert data["status"] == "saved"
        mock_job_repo.create.assert_called_once()
        mock_app_repo.create.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_add_job_manually_requires_title(client: AsyncClient) -> None:
    """POST /jobs/manual without required title field should return 422."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        response = await client.post("/jobs/manual", json={"company_name": "Acme"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /jobs
# ---------------------------------------------------------------------------


async def test_list_jobs_returns_summaries(client: AsyncClient) -> None:
    """GET /jobs should return a list of job summaries for the current user."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_job = _make_job(job_id)
    fake_application = _make_application(job_id=job_id, user_id=user_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_for_user.return_value = [fake_application]

    mock_job_repo = AsyncMock()
    mock_job_repo.find_by_ids.return_value = [fake_job]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Senior Engineer"
        assert data[0]["company_name"] == "Acme Corp"
    finally:
        app.dependency_overrides.clear()


async def test_list_jobs_empty(client: AsyncClient) -> None:
    """GET /jobs returns empty list when user has no applications."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_for_user.return_value = []
    mock_job_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /jobs/{job_id}
# ---------------------------------------------------------------------------


async def test_get_job_returns_detail(client: AsyncClient) -> None:
    """GET /jobs/{id} returns full detail for the owner."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_job = _make_job(job_id)
    fake_application = _make_application(job_id=job_id, user_id=user_id)

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Senior Engineer"
        assert data["description"] == "A great job"
    finally:
        app.dependency_overrides.clear()


async def test_get_job_404_for_nonexistent(client: AsyncClient) -> None:
    """GET /jobs/{id} returns 404 when job does not exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = None
    mock_app_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs/111111111111111111111111")
        assert response.status_code == 404
        assert response.json()["error_code"] == "JOB_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_get_job_403_when_no_application(client: AsyncClient) -> None:
    """GET /jobs/{id} returns 403 when user has no application for this job."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_job = _make_job()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(f"/jobs/{fake_job.id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: DELETE /jobs/{job_id}
# ---------------------------------------------------------------------------


async def test_delete_job_returns_204(client: AsyncClient) -> None:
    """DELETE /jobs/{id} deletes job and application, returns 204."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_job = _make_job(job_id)
    fake_application = _make_application(job_id=job_id, user_id=user_id)

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.return_value = True

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.return_value = True

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = []
    mock_doc_repo.delete_for_application.return_value = 0

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.return_value = 0

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=AsyncMock(),
        ):
            response = await client.delete(f"/jobs/{job_id}")
        assert response.status_code == 204
        mock_app_repo.delete.assert_called_once()
        mock_job_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_404_for_nonexistent(client: AsyncClient) -> None:
    """DELETE /jobs/{id} returns 404 when job does not exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = None
    mock_app_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.delete("/jobs/111111111111111111111111")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: match_score / match_reasoning excluded from responses
# ---------------------------------------------------------------------------


async def test_list_jobs_excludes_match_score(client: AsyncClient) -> None:
    """GET /jobs response items must NOT contain match_score or match_reasoning."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_job = _make_job(job_id)
    fake_application = _make_application(job_id=job_id, user_id=user_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_for_user.return_value = [fake_application]

    mock_job_repo = AsyncMock()
    mock_job_repo.find_by_ids.return_value = [fake_job]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get("/jobs")
        assert response.status_code == 200
        for job in response.json():
            assert "match_score" not in job
            assert "match_reasoning" not in job
    finally:
        app.dependency_overrides.clear()


async def test_get_job_detail_excludes_match_fields(client: AsyncClient) -> None:
    """GET /jobs/{id} response must NOT contain match_score or match_reasoning."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_job = _make_job(job_id)
    fake_application = _make_application(job_id=job_id, user_id=user_id)

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert "match_score" not in data
        assert "match_reasoning" not in data
    finally:
        app.dependency_overrides.clear()
