"""
Tests for interview CRUD endpoints.

Story 5.2: Interview schedule management — create, list, get, update, delete.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_interview_repository,
    get_job_repository,
)
from src.db.documents.application import Application
from src.db.documents.enums import InterviewType
from src.db.documents.interview import Interview, InterviewNotes
from src.db.documents.job import Job, JobRequirements

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
APP_ID = "bbbbbbbbbbbbbbbbbbbbbbbb"
JOB_ID = "cccccccccccccccccccccccc"
INTERVIEW_ID = "dddddddddddddddddddddddd"


def _make_user(user_id: str = USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_application(app_id: str = APP_ID, user_id: str = USER_ID, job_id: str = JOB_ID):
    app = MagicMock(spec=Application)
    app.id = PydanticObjectId(app_id)
    app.user_id = PydanticObjectId(user_id)
    app.job_id = PydanticObjectId(job_id)
    app.status = "applied"
    return app


def _make_job(job_id: str = JOB_ID):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Senior Engineer"
    job.company_name = "TechCorp"
    job.requirements = JobRequirements()
    return job


def _make_interview(
    interview_id: str = INTERVIEW_ID,
    user_id: str = USER_ID,
    app_id: str = APP_ID,
):
    interview = MagicMock(spec=Interview)
    interview.id = PydanticObjectId(interview_id)
    interview.user_id = PydanticObjectId(user_id)
    interview.application_id = PydanticObjectId(app_id)
    interview.scheduled_at = None
    interview.interview_type = InterviewType.TECHNICAL
    interview.company_name = "TechCorp"
    interview.role_title = "Senior Engineer"
    interview.interviewer_name = "Jane Smith"
    interview.notes = InterviewNotes(key_points=["Good fit"], follow_up_items=[])
    interview.questions = []
    interview.preparation_notes = ""
    interview.created_at = None
    interview.updated_at = None
    return interview


def _setup(app, mock_interview_repo, mock_app_repo=None, mock_job_repo=None, fake_user=None):
    app.dependency_overrides[get_current_user] = lambda: (fake_user or _make_user())
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo
    if mock_app_repo:
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    if mock_job_repo:
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo


# ---------------------------------------------------------------------------
# Tests: POST /interviews
# ---------------------------------------------------------------------------


class TestCreateInterview:

    async def test_create_returns_201_with_denormalized_fields(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_user = _make_user()
        fake_app = _make_application()
        fake_job = _make_job()
        fake_interview = _make_interview()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.create.return_value = fake_interview

        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = fake_app

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = fake_job

        _setup(app, mock_interview_repo, mock_app_repo, mock_job_repo, fake_user)

        try:
            response = await client.post(
                "/interviews",
                json={
                    "application_id": APP_ID,
                    "interview_type": "technical",
                    "interviewer_name": "Jane Smith",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["company_name"] == "TechCorp"
            assert data["role_title"] == "Senior Engineer"
            assert data["user_id"] == USER_ID
            # Verify create was called with correct user_id
            create_arg = mock_interview_repo.create.call_args.args[0]
            assert create_arg.user_id == fake_user.id
        finally:
            app.dependency_overrides.clear()

    async def test_create_returns_404_when_application_not_found(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = None
        mock_job_repo = AsyncMock()

        _setup(app, mock_interview_repo, mock_app_repo, mock_job_repo)

        try:
            response = await client.post(
                "/interviews",
                json={"application_id": APP_ID, "interview_type": "technical"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_create_returns_404_for_other_users_application(self, client: AsyncClient):
        """get_by_user_and_id returns None for other user's app."""
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = None
        mock_job_repo = AsyncMock()

        _setup(app, mock_interview_repo, mock_app_repo, mock_job_repo)

        try:
            response = await client.post(
                "/interviews",
                json={"application_id": APP_ID, "interview_type": "technical"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_create_returns_401_without_auth(self, client: AsyncClient):
        response = await client.post(
            "/interviews",
            json={"application_id": APP_ID, "interview_type": "technical"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interviews
# ---------------------------------------------------------------------------


class TestListInterviews:

    async def test_list_returns_user_interviews(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_interview = _make_interview()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_for_user.return_value = [fake_interview]
        _setup(app, mock_interview_repo)

        try:
            response = await client.get("/interviews")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["company_name"] == "TechCorp"
        finally:
            app.dependency_overrides.clear()

    async def test_list_filters_by_application_id(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_for_user.return_value = []
        _setup(app, mock_interview_repo)

        try:
            await client.get(f"/interviews?application_id={APP_ID}")
            call_kwargs = mock_interview_repo.get_for_user.call_args
            assert call_kwargs.kwargs["application_id"] == PydanticObjectId(APP_ID)
        finally:
            app.dependency_overrides.clear()

    async def test_list_empty_returns_empty_list(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_for_user.return_value = []
        _setup(app, mock_interview_repo)

        try:
            response = await client.get("/interviews")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_returns_401_without_auth(self, client: AsyncClient):
        response = await client.get("/interviews")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interviews/{id}
# ---------------------------------------------------------------------------


class TestGetInterview:

    async def test_get_returns_interview(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_interview = _make_interview()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = fake_interview
        _setup(app, mock_interview_repo)

        try:
            response = await client.get(f"/interviews/{INTERVIEW_ID}")
            assert response.status_code == 200
            assert response.json()["id"] == INTERVIEW_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_interview_repo)

        try:
            response = await client.get(f"/interviews/{INTERVIEW_ID}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_get_returns_401_without_auth(self, client: AsyncClient):
        response = await client.get(f"/interviews/{INTERVIEW_ID}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: PATCH /interviews/{id}
# ---------------------------------------------------------------------------


class TestUpdateInterview:

    async def test_update_returns_updated_interview(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_interview = _make_interview()
        updated_interview = _make_interview()
        updated_interview.interviewer_name = "John Doe"

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = fake_interview
        mock_interview_repo.update.return_value = updated_interview
        _setup(app, mock_interview_repo)

        try:
            response = await client.patch(
                f"/interviews/{INTERVIEW_ID}",
                json={"interviewer_name": "John Doe"},
            )
            assert response.status_code == 200
            assert response.json()["interviewer_name"] == "John Doe"
            mock_interview_repo.update.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_update_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_interview_repo)

        try:
            response = await client.patch(
                f"/interviews/{INTERVIEW_ID}",
                json={"interviewer_name": "John Doe"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_update_returns_401_without_auth(self, client: AsyncClient):
        response = await client.patch(
            f"/interviews/{INTERVIEW_ID}",
            json={"interviewer_name": "John Doe"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: DELETE /interviews/{id}
# ---------------------------------------------------------------------------


class TestDeleteInterview:

    async def test_delete_returns_204(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_interview = _make_interview()

        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = fake_interview
        mock_interview_repo.delete.return_value = None
        _setup(app, mock_interview_repo)

        try:
            response = await client.delete(f"/interviews/{INTERVIEW_ID}")
            assert response.status_code == 204
            assert response.content == b""
            mock_interview_repo.delete.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_interview_repo = AsyncMock()
        mock_interview_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_interview_repo)

        try:
            response = await client.delete(f"/interviews/{INTERVIEW_ID}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_delete_returns_401_without_auth(self, client: AsyncClient):
        response = await client.delete(f"/interviews/{INTERVIEW_ID}")
        assert response.status_code == 401
