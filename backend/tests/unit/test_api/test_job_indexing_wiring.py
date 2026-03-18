"""
Tests for the job indexing wiring in the add_job_manually route.

Verifies that _index_job_background correctly calls IndexingService.index_job(),
handles indexing errors gracefully (no crash), skips indexing when job description
is empty, and that the route queues the background task with correct user_id.

These tests patch build_indexing_service to inject a mock IndexingService,
avoiding any real database or Weaviate calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
    get_job_repository,
)
from src.api.routes.jobs import _index_job_background
from src.db.documents.application import Application
from src.db.documents.enums import ApplicationStatus
from src.db.documents.job import Job, JobRequirements

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FAKE_JOB_ID = "111111111111111111111111"
FAKE_USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"


def _make_user(user_id: str = FAKE_USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_job(job_id: str = FAKE_JOB_ID, description: str = "A great job"):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Senior Engineer"
    job.company_name = "Acme Corp"
    job.company_id = None
    job.description = description
    job.location = "Remote"
    job.remote = True
    job.url = "https://example.com/job"
    job.source = "manual"
    job.requirements = JobRequirements(required_skills=["python"], preferred_skills=[])
    job.created_at = None
    return job


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = FAKE_USER_ID,
    job_id: str = FAKE_JOB_ID,
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
# Tests: Task 3.1 — _index_job_background calls index_job with correct args
# ---------------------------------------------------------------------------


class TestIndexJobBackgroundCallsIndexJob:
    """Verify _index_job_background calls IndexingService.index_job()."""

    async def test_calls_index_job_with_correct_args(self):
        """index_job should be called with job_id and user_id."""
        mock_service = AsyncMock()
        mock_service.index_job = AsyncMock(return_value=None)

        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_service,
        ):
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)

        mock_service.index_job.assert_called_once_with(FAKE_JOB_ID, FAKE_USER_ID)

    async def test_logs_success_on_completion(self):
        """Successful indexing should log job_indexing_completed."""
        mock_service = AsyncMock()
        mock_service.index_job = AsyncMock(return_value=None)

        with (
            patch(
                "src.api.routes.jobs.build_indexing_service",
                return_value=mock_service,
            ),
            patch("src.api.routes.jobs.logger") as mock_logger,
        ):
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)

        mock_logger.info.assert_any_call(
            "job_indexing_completed",
            job_id=FAKE_JOB_ID,
            user_id=FAKE_USER_ID,
        )


# ---------------------------------------------------------------------------
# Tests: Task 3.2 — _index_job_background logs error but does NOT crash
# ---------------------------------------------------------------------------


class TestIndexJobBackgroundHandlesFailure:
    """Verify indexing errors are caught and logged, not propagated."""

    async def test_does_not_crash_on_indexing_error(self):
        """Indexing failure should be caught and logged — must not raise."""
        mock_service = AsyncMock()
        mock_service.index_job = AsyncMock(
            side_effect=Exception("Weaviate down")
        )

        with (
            patch(
                "src.api.routes.jobs.build_indexing_service",
                return_value=mock_service,
            ),
            patch("src.api.routes.jobs.logger") as mock_logger,
        ):
            # Must NOT raise
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)

        mock_logger.exception.assert_called_once_with(
            "job_indexing_failed",
            job_id=FAKE_JOB_ID,
            user_id=FAKE_USER_ID,
        )

    async def test_does_not_crash_on_service_build_failure(self):
        """If build_indexing_service itself fails, background task must not raise."""
        with (
            patch(
                "src.api.routes.jobs.build_indexing_service",
                side_effect=Exception("Cannot build service"),
            ),
            patch("src.api.routes.jobs.logger") as mock_logger,
        ):
            # Must NOT raise
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)

        mock_logger.exception.assert_called_once_with(
            "job_indexing_failed",
            job_id=FAKE_JOB_ID,
            user_id=FAKE_USER_ID,
        )


# ---------------------------------------------------------------------------
# Tests: Task 3.3 — indexing skipped when job description is empty
# ---------------------------------------------------------------------------


class TestAddJobManuallySkipsIndexingNoDescription:
    """Verify route skips indexing when job has no description."""

    async def test_skips_indexing_when_description_empty(
        self, client: AsyncClient
    ):
        """No background task should be queued when description is empty."""
        app = client.app  # type: ignore[attr-defined]

        fake_user = _make_user()
        fake_job = _make_job(description="")
        fake_application = _make_application()

        mock_job_repo = AsyncMock()
        mock_job_repo.create.return_value = fake_job
        mock_app_repo = AsyncMock()
        mock_app_repo.create.return_value = fake_application

        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

        try:
            with patch("src.api.routes.jobs.logger") as mock_logger:
                response = await client.post(
                    "/jobs/manual",
                    json={"title": "Engineer", "company_name": "Acme"},
                )
                assert response.status_code == 201
                mock_logger.info.assert_any_call(
                    "job_indexing_skipped_no_description",
                    job_id=str(fake_job.id),
                    user_id=str(fake_user.id),
                )
        finally:
            app.dependency_overrides.clear()

    async def test_skips_indexing_when_description_whitespace(
        self, client: AsyncClient
    ):
        """No background task should be queued when description is only whitespace."""
        app = client.app  # type: ignore[attr-defined]

        fake_user = _make_user()
        fake_job = _make_job(description="   \n  ")
        fake_application = _make_application()

        mock_job_repo = AsyncMock()
        mock_job_repo.create.return_value = fake_job
        mock_app_repo = AsyncMock()
        mock_app_repo.create.return_value = fake_application

        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

        try:
            with patch("src.api.routes.jobs.logger") as mock_logger:
                response = await client.post(
                    "/jobs/manual",
                    json={"title": "Engineer", "company_name": "Acme"},
                )
                assert response.status_code == 201
                mock_logger.info.assert_any_call(
                    "job_indexing_skipped_no_description",
                    job_id=str(fake_job.id),
                    user_id=str(fake_user.id),
                )
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: Task 3.4 — route queues background task with correct user_id
# ---------------------------------------------------------------------------


class TestAddJobManuallyQueuesIndexing:
    """Verify route queues _index_job_background with correct args."""

    async def test_queues_background_task_with_user_id(
        self, client: AsyncClient
    ):
        """Background task should receive str(current_user.id) as user_id."""
        app = client.app  # type: ignore[attr-defined]

        fake_user = _make_user()
        fake_job = _make_job(description="A real job description for indexing")
        fake_application = _make_application()

        mock_job_repo = AsyncMock()
        mock_job_repo.create.return_value = fake_job
        mock_app_repo = AsyncMock()
        mock_app_repo.create.return_value = fake_application

        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

        try:
            with patch(
                "src.api.routes.jobs._index_job_background"
            ) as mock_bg:
                response = await client.post(
                    "/jobs/manual",
                    json={
                        "title": "Senior Engineer",
                        "company_name": "Acme Corp",
                        "description": "A real job description for indexing",
                    },
                )
                assert response.status_code == 201
                # BackgroundTasks runs inline in test client — verify args
                mock_bg.assert_called_once_with(
                    str(fake_job.id), str(fake_user.id)
                )
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: Task 3.5 — idempotent re-indexing
# ---------------------------------------------------------------------------


class TestIdempotentReIndexingViaBackgroundTask:
    """Verify consecutive calls to _index_job_background invoke index_job each time.

    The actual delete-before-reindex logic is in IndexingService (tested in
    test_indexing_service.py). This test confirms the wiring supports re-indexing.
    """

    async def test_consecutive_calls_invoke_index_job_each_time(self):
        """Re-indexing should call index_job again (idempotent)."""
        mock_service = AsyncMock()
        mock_service.index_job = AsyncMock(return_value=None)

        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_service,
        ):
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)
            await _index_job_background(FAKE_JOB_ID, FAKE_USER_ID)

        assert mock_service.index_job.call_count == 2
