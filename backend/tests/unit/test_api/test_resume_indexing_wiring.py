"""
Tests for the resume indexing wiring in the background parse task.

Verifies that _parse_resume_background correctly calls IndexingService.index_resume()
after a successful parse, handles indexing errors gracefully, and does NOT call
index_resume when the parse itself fails.

These tests patch _build_indexing_service to inject a mock IndexingService,
avoiding any real database or Weaviate calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.profile import _parse_resume_background

_REPO_PATCH = "src.api.routes.profile.ResumeRepository"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_RESUME_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
FAKE_USER_ID = "bbbbbbbbbbbbbbbbbbbbbbbb"
FAKE_RAW_TEXT = "Education\nBS Computer Science\n\nSkills\nPython, FastAPI"


@pytest.fixture
def mock_indexing_service():
    """Create a mock IndexingService."""
    service = AsyncMock()
    service.index_resume = AsyncMock(return_value=3)
    return service


@pytest.fixture(autouse=True)
def mock_resume_repo():
    """Patch ResumeRepository used for parse_status transitions in background task."""
    mock_repo = AsyncMock()
    mock_repo.update = AsyncMock(return_value=None)
    with patch(_REPO_PATCH, return_value=mock_repo):
        yield mock_repo


# ---------------------------------------------------------------------------
# Tests: Task 4.1 — background task calls index_resume on successful parse
# ---------------------------------------------------------------------------


class TestParseResumeBackgroundCallsIndexing:
    """Verify _parse_resume_background calls index_resume on success."""

    async def test_calls_index_resume_with_correct_args(
        self, mock_indexing_service
    ):
        """index_resume should be called with resume_id and user_id."""
        with patch(
            "src.api.routes.profile.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)

        mock_indexing_service.index_resume.assert_called_once_with(
            FAKE_RESUME_ID, FAKE_USER_ID
        )

    async def test_logs_chunk_count_on_success(self, mock_indexing_service):
        """Successful indexing should log the chunk count."""
        with (
            patch(
                "src.api.routes.profile.build_indexing_service",
                return_value=mock_indexing_service,
            ),
            patch("src.api.routes.profile.logger") as mock_logger,
        ):
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)

        mock_logger.info.assert_any_call(
            "resume_indexing_completed",
            resume_id=FAKE_RESUME_ID,
            user_id=FAKE_USER_ID,
            chunk_count=3,
        )


# ---------------------------------------------------------------------------
# Tests: Task 4.2 — background task logs error but does NOT crash on failure
# ---------------------------------------------------------------------------


class TestParseResumeBackgroundHandlesIndexingFailure:
    """Verify indexing errors are caught and logged, not propagated."""

    async def test_does_not_crash_on_indexing_error(self, mock_indexing_service):
        """Indexing failure should be caught and logged — background task must not raise."""
        mock_indexing_service.index_resume = AsyncMock(
            side_effect=Exception("Weaviate connection failed")
        )

        with (
            patch(
                "src.api.routes.profile.build_indexing_service",
                return_value=mock_indexing_service,
            ),
            patch("src.api.routes.profile.logger") as mock_logger,
        ):
            # Must NOT raise
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)

        mock_logger.exception.assert_called_once_with(
            "resume_indexing_failed",
            resume_id=FAKE_RESUME_ID,
            user_id=FAKE_USER_ID,
        )

    async def test_does_not_crash_on_service_build_failure(self):
        """If _build_indexing_service itself fails, background task must not raise."""
        with patch(
            "src.api.routes.profile.build_indexing_service",
            side_effect=Exception("Cannot build service"),
        ):
            # Must NOT raise
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)


# ---------------------------------------------------------------------------
# Tests: Task 4.3 — does NOT call index_resume when parse fails
# ---------------------------------------------------------------------------


class TestParseResumeBackgroundSkipsIndexingOnParseFailure:
    """Verify index_resume is NOT called when raw_text is empty (parse failed)."""

    async def test_skips_indexing_when_raw_text_empty(self, mock_indexing_service):
        """If raw_text is empty, indexing should be skipped."""
        with patch(
            "src.api.routes.profile.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            await _parse_resume_background(FAKE_RESUME_ID, "", FAKE_USER_ID)

        mock_indexing_service.index_resume.assert_not_called()

    async def test_skips_indexing_when_raw_text_whitespace(self, mock_indexing_service):
        """If raw_text is only whitespace, indexing should be skipped."""
        with patch(
            "src.api.routes.profile.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            await _parse_resume_background(FAKE_RESUME_ID, "   \n  ", FAKE_USER_ID)

        mock_indexing_service.index_resume.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Task 2.3 — idempotent re-indexing via background task
# ---------------------------------------------------------------------------


class TestIdempotentReIndexingViaBackgroundTask:
    """Verify that calling _parse_resume_background twice calls index_resume twice.

    The actual delete-before-reindex logic is in IndexingService (tested in
    test_indexing_service.py). This test confirms the wiring supports re-indexing
    by invoking the same path multiple times.
    """

    async def test_consecutive_calls_invoke_index_resume_each_time(
        self, mock_indexing_service
    ):
        """Re-uploading should call index_resume again (idempotent re-index)."""
        with patch(
            "src.api.routes.profile.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)
            await _parse_resume_background(FAKE_RESUME_ID, FAKE_RAW_TEXT, FAKE_USER_ID)

        assert mock_indexing_service.index_resume.call_count == 2


