"""
Unit tests for application pipeline tracking routes.

Key coverage:
- GET /track/kanban returns grouped dict by status
- PATCH status with valid transition succeeds
- PATCH status with invalid transition returns 422 + INVALID_STATUS_TRANSITION
- PATCH notes updates notes field

Why client.app (not `from src.api.main import app`):
    The `client` fixture creates a fresh FastAPI instance via create_app().
    The module-level `app` singleton is a separate object. Overrides must
    be applied to the same instance the client is sending requests to.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_job_repository,
)
from src.db.documents.application import Application
from src.api.routes.track import ACTIVE_STATUSES
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
    job.title = "Software Engineer"
    job.company_name = "Acme"
    job.requirements = JobRequirements()
    return job


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
    job_id: str = "111111111111111111111111",
    status: ApplicationStatus = ApplicationStatus.SAVED,
):
    application = MagicMock(spec=Application)
    application.id = PydanticObjectId(app_id)
    application.user_id = PydanticObjectId(user_id)
    application.job_id = PydanticObjectId(job_id)
    application.status = status
    application.match_score = None
    application.applied_at = None
    application.notes = ""
    application.created_at = None
    return application


# ---------------------------------------------------------------------------
# Tests: GET /track/kanban
# ---------------------------------------------------------------------------


async def test_get_kanban_returns_grouped_dict(client: AsyncClient) -> None:
    """GET /track/kanban returns all statuses as keys with application lists."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_application = _make_application(
        job_id=job_id, user_id=user_id, status=ApplicationStatus.SAVED
    )
    fake_job = _make_job(job_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_kanban.return_value = [fake_application]

    mock_job_repo = AsyncMock()
    mock_job_repo.find_by_ids.return_value = [fake_job]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo

    try:
        response = await client.get("/track/kanban")
        assert response.status_code == 200
        data = response.json()
        # Only active status keys should be present
        for status in ACTIVE_STATUSES:
            assert status.value in data
        # The saved application should be in the "saved" bucket
        assert len(data[ApplicationStatus.SAVED.value]) == 1
        assert data[ApplicationStatus.SAVED.value][0]["job_title"] == "Software Engineer"
    finally:
        app.dependency_overrides.clear()


async def test_get_kanban_empty_returns_all_status_keys(client: AsyncClient) -> None:
    """GET /track/kanban with no applications returns all status keys with empty lists."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_kanban.return_value = []
    mock_job_repo = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo

    try:
        response = await client.get("/track/kanban")
        assert response.status_code == 200
        data = response.json()
        for status in ACTIVE_STATUSES:
            assert status.value in data
            assert data[status.value] == []
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: PATCH /track/applications/{id}/status
# ---------------------------------------------------------------------------


async def test_update_status_valid_transition(client: AsyncClient) -> None:
    """PATCH status with valid transition (SAVED -> APPLIED) returns 200."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    app_id = "222222222222222222222222"

    fake_user = _make_user(user_id)
    fake_application = _make_application(
        app_id=app_id, user_id=user_id, status=ApplicationStatus.SAVED
    )

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application
    mock_app_repo.update.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            f"/track/applications/{app_id}/status",
            json={"status": "applied"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["old_status"] == "saved"
        assert data["new_status"] == "applied"
        mock_app_repo.update.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_update_status_invalid_transition_returns_422(client: AsyncClient) -> None:
    """PATCH status with invalid transition returns 422 with INVALID_STATUS_TRANSITION."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    app_id = "222222222222222222222222"

    fake_user = _make_user(user_id)
    # ACCEPTED is a terminal state — no transitions allowed
    fake_application = _make_application(
        app_id=app_id, user_id=user_id, status=ApplicationStatus.ACCEPTED
    )

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            f"/track/applications/{app_id}/status",
            json={"status": "applied"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "INVALID_STATUS_TRANSITION"
    finally:
        app.dependency_overrides.clear()


async def test_update_status_404_for_nonexistent_application(client: AsyncClient) -> None:
    """PATCH status for non-existent application returns 404."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            "/track/applications/222222222222222222222222/status",
            json={"status": "applied"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: PATCH /track/applications/{id}/notes
# ---------------------------------------------------------------------------


async def test_update_notes_returns_updated_notes(client: AsyncClient) -> None:
    """PATCH notes updates the notes field and returns it."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    app_id = "222222222222222222222222"

    fake_user = _make_user(user_id)
    fake_application = _make_application(app_id=app_id, user_id=user_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application
    mock_app_repo.update.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            f"/track/applications/{app_id}/notes",
            json={"notes": "Great company, applied via referral"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Great company, applied via referral"
        assert data["application_id"] == app_id
        mock_app_repo.update.assert_called_once_with(
            fake_application.id, {"notes": "Great company, applied via referral"}
        )
    finally:
        app.dependency_overrides.clear()


async def test_update_notes_404_for_nonexistent(client: AsyncClient) -> None:
    """PATCH notes for non-existent application returns 404."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            "/track/applications/222222222222222222222222/notes",
            json={"notes": "some notes"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: match_score excluded from responses
# ---------------------------------------------------------------------------


async def test_kanban_excludes_match_score(client: AsyncClient) -> None:
    """GET /track/kanban items must NOT contain match_score."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_application = _make_application(
        job_id=job_id, user_id=user_id, status=ApplicationStatus.SAVED
    )
    fake_job = _make_job(job_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_kanban.return_value = [fake_application]

    mock_job_repo = AsyncMock()
    mock_job_repo.find_by_ids.return_value = [fake_job]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo

    try:
        response = await client.get("/track/kanban")
        assert response.status_code == 200
        data = response.json()
        for status_items in data.values():
            for item in status_items:
                assert "match_score" not in item
    finally:
        app.dependency_overrides.clear()


async def test_list_applications_excludes_match_score(client: AsyncClient) -> None:
    """GET /track/applications items must NOT contain match_score."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    job_id = "111111111111111111111111"

    fake_user = _make_user(user_id)
    fake_application = _make_application(
        job_id=job_id, user_id=user_id, status=ApplicationStatus.SAVED
    )
    fake_job = _make_job(job_id)

    mock_app_repo = AsyncMock()
    mock_app_repo.get_for_user.return_value = [fake_application]

    mock_job_repo = AsyncMock()
    mock_job_repo.find_by_ids.return_value = [fake_job]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo

    try:
        response = await client.get("/track/applications")
        assert response.status_code == 200
        for item in response.json():
            assert "match_score" not in item
    finally:
        app.dependency_overrides.clear()
