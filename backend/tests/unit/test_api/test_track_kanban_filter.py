"""
Tests for kanban filtering (active-only) and archive endpoint.

Story 4.1: Scope kanban to active applications and add archive endpoint.

Coverage:
- GET /track/kanban excludes terminal statuses
- GET /track/kanban response keys only include active statuses
- GET /track/kanban with no active applications returns empty active-status keys
- GET /track/applications/archive returns only terminal statuses
- GET /track/applications/archive respects pagination params
- GET /track/applications/archive returns 401 without auth
- ApplicationRepository.get_kanban() passes correct filter
- ApplicationRepository.get_for_user_by_statuses() passes correct $in filter
- Transitioning to REJECTED removes app from kanban
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_job_repository,
)
from src.api.routes.track import ACTIVE_STATUSES, TERMINAL_STATUSES
from src.db.documents.application import Application
from src.db.documents.enums import ApplicationStatus
from src.db.documents.job import Job, JobRequirements

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
JOB_ID = "111111111111111111111111"


def _make_user(user_id: str = USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_job(job_id: str = JOB_ID):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Software Engineer"
    job.company_name = "Acme"
    job.requirements = JobRequirements()
    return job


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = USER_ID,
    job_id: str = JOB_ID,
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


def _setup_overrides(app, mock_app_repo, mock_job_repo, fake_user=None):
    """Apply dependency overrides for track route tests."""
    app.dependency_overrides[get_current_user] = lambda: (fake_user or _make_user())
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo


# ---------------------------------------------------------------------------
# Tests: GET /track/kanban — only active statuses
# ---------------------------------------------------------------------------


class TestKanbanExcludesTerminalStatuses:
    """Verify kanban returns only active-status applications."""

    async def test_kanban_response_keys_are_active_only(self, client: AsyncClient):
        """Response dict should only have active status keys, not terminal ones."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_kanban.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            response = await client.get("/track/kanban")
            assert response.status_code == 200
            data = response.json()
            for status in ACTIVE_STATUSES:
                assert status.value in data
            for status in TERMINAL_STATUSES:
                assert status.value not in data
        finally:
            app.dependency_overrides.clear()

    async def test_kanban_calls_repo_with_exclude_statuses(self, client: AsyncClient):
        """get_kanban should be called with exclude_statuses=TERMINAL_STATUSES."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_kanban.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            await client.get("/track/kanban")
            mock_app_repo.get_kanban.assert_called_once()
            call_kwargs = mock_app_repo.get_kanban.call_args
            exclude = call_kwargs.kwargs.get("exclude_statuses", [])
            assert set(exclude) == set(TERMINAL_STATUSES)
        finally:
            app.dependency_overrides.clear()

    async def test_kanban_empty_returns_active_status_keys_with_empty_lists(
        self, client: AsyncClient
    ):
        """Empty kanban returns active-status keys with empty lists."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_kanban.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            response = await client.get("/track/kanban")
            data = response.json()
            assert len(data) == len(ACTIVE_STATUSES)
            for status in ACTIVE_STATUSES:
                assert data[status.value] == []
        finally:
            app.dependency_overrides.clear()

    async def test_kanban_only_returns_active_applications(self, client: AsyncClient):
        """Only active-status applications appear in the kanban response."""
        app = client.app  # type: ignore[attr-defined]
        fake_user = _make_user()

        # Repo returns only active apps (the filtering happened at DB level)
        active_app = _make_application(status=ApplicationStatus.APPLIED)
        mock_app_repo = AsyncMock()
        mock_app_repo.get_kanban.return_value = [active_app]

        mock_job_repo = AsyncMock()
        mock_job_repo.find_by_ids.return_value = [_make_job()]
        _setup_overrides(app, mock_app_repo, mock_job_repo, fake_user)

        try:
            response = await client.get("/track/kanban")
            data = response.json()
            assert len(data["applied"]) == 1
            assert data["saved"] == []
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /track/applications/archive
# ---------------------------------------------------------------------------


class TestArchiveEndpoint:
    """Verify archive endpoint returns only terminal-status applications."""

    async def test_archive_returns_terminal_statuses(self, client: AsyncClient):
        """Archive endpoint should return applications with terminal statuses."""
        app = client.app  # type: ignore[attr-defined]
        fake_user = _make_user()

        rejected_app = _make_application(
            app_id="333333333333333333333333", status=ApplicationStatus.REJECTED
        )
        mock_app_repo = AsyncMock()
        mock_app_repo.get_for_user_by_statuses.return_value = [rejected_app]

        mock_job_repo = AsyncMock()
        mock_job_repo.find_by_ids.return_value = [_make_job()]
        _setup_overrides(app, mock_app_repo, mock_job_repo, fake_user)

        try:
            response = await client.get("/track/applications/archive")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "rejected"
        finally:
            app.dependency_overrides.clear()

    async def test_archive_calls_repo_with_terminal_statuses(
        self, client: AsyncClient
    ):
        """Archive should call get_for_user_by_statuses with TERMINAL_STATUSES."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_for_user_by_statuses.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            await client.get("/track/applications/archive")
            mock_app_repo.get_for_user_by_statuses.assert_called_once()
            call_kwargs = mock_app_repo.get_for_user_by_statuses.call_args
            statuses = call_kwargs.kwargs.get("statuses", [])
            assert set(statuses) == set(TERMINAL_STATUSES)
        finally:
            app.dependency_overrides.clear()

    async def test_archive_respects_pagination_params(self, client: AsyncClient):
        """Archive should pass skip and limit to the repository."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_for_user_by_statuses.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            await client.get("/track/applications/archive?skip=10&limit=25")
            call_kwargs = mock_app_repo.get_for_user_by_statuses.call_args
            assert call_kwargs.kwargs.get("skip") == 10
            assert call_kwargs.kwargs.get("limit") == 25
        finally:
            app.dependency_overrides.clear()

    async def test_archive_empty_returns_empty_list(self, client: AsyncClient):
        """Archive with no terminal applications returns empty list."""
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_for_user_by_statuses.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo)

        try:
            response = await client.get("/track/applications/archive")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_archive_returns_401_without_auth(self, client: AsyncClient):
        """Archive endpoint requires authentication."""
        response = await client.get("/track/applications/archive")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Repository methods
# ---------------------------------------------------------------------------


class TestApplicationRepositoryKanbanFilter:
    """Verify get_kanban passes correct filter when exclude_statuses provided."""

    async def test_get_kanban_passes_nin_filter(self):
        """get_kanban with exclude_statuses should build $nin query."""
        from src.repositories.application_repository import ApplicationRepository

        repo = ApplicationRepository.__new__(ApplicationRepository)
        repo.find_many = AsyncMock(return_value=[])

        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        exclude = [ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]
        await repo.get_kanban(user_id, exclude_statuses=exclude)

        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == user_id
        assert "$nin" in str(filters["status"])
        assert set(filters["status"]["$nin"]) == {"rejected", "withdrawn"}

    async def test_get_kanban_no_exclude_has_no_status_filter(self):
        """get_kanban without exclude_statuses should not filter by status."""
        from src.repositories.application_repository import ApplicationRepository

        repo = ApplicationRepository.__new__(ApplicationRepository)
        repo.find_many = AsyncMock(return_value=[])

        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        await repo.get_kanban(user_id)

        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert "status" not in filters


class TestApplicationRepositoryGetByStatuses:
    """Verify get_for_user_by_statuses passes correct $in filter."""

    async def test_passes_in_filter(self):
        """get_for_user_by_statuses should build $in query."""
        from src.repositories.application_repository import ApplicationRepository

        repo = ApplicationRepository.__new__(ApplicationRepository)
        repo.find_many = AsyncMock(return_value=[])

        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        statuses = [ApplicationStatus.REJECTED, ApplicationStatus.ACCEPTED]
        await repo.get_for_user_by_statuses(user_id, statuses, skip=5, limit=10)

        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == user_id
        assert set(filters["status"]["$in"]) == {"rejected", "accepted"}
        assert call_args.kwargs["skip"] == 5
        assert call_args.kwargs["limit"] == 10
        assert call_args.kwargs["sort"] == "-created_at"


# ---------------------------------------------------------------------------
# Tests: Transition removes from kanban
# ---------------------------------------------------------------------------


class TestTransitionRemovesFromKanban:
    """Verify that terminal-status apps don't appear in kanban."""

    async def test_rejected_app_not_in_kanban(self, client: AsyncClient):
        """After transitioning to REJECTED, app should not appear in kanban."""
        app = client.app  # type: ignore[attr-defined]
        fake_user = _make_user()

        # Kanban repo returns no apps (the rejected one is filtered out at DB level)
        mock_app_repo = AsyncMock()
        mock_app_repo.get_kanban.return_value = []
        mock_job_repo = AsyncMock()
        _setup_overrides(app, mock_app_repo, mock_job_repo, fake_user)

        try:
            response = await client.get("/track/kanban")
            data = response.json()
            for status_key in data:
                assert data[status_key] == []
        finally:
            app.dependency_overrides.clear()
