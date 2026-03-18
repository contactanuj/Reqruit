"""
Tests for DocumentRepository — atomic version assignment and conflict handling.

Story 2.1: Enforce Atomic Document Version Assignment
Covers:
  - Unique compound index on (application_id, doc_type, version)
  - create_versioned() happy path, retry on DuplicateKeyError, ConflictError on exhaustion
  - Integration with start_cover_letter endpoint (409 on version conflict)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from src.core.exceptions import ConflictError
from src.db.documents.document_record import DocumentRecord
from src.db.documents.enums import DocumentType
from src.repositories.document_repository import DocumentRepository

# ---------------------------------------------------------------------------
# Task 1: Index definition tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Task 5 (Story 2.4): Thread ownership lookup tests
# ---------------------------------------------------------------------------


class TestGetByThreadIdAndUser:
    """Tests for DocumentRepository.get_by_thread_id_and_user()."""

    @pytest.fixture()
    def repo(self) -> DocumentRepository:
        return DocumentRepository()

    async def test_returns_document_when_thread_and_user_match(
        self, repo: DocumentRepository
    ) -> None:
        """Returns DocumentRecord when thread_id and user_id both match."""
        user_id = PydanticObjectId()
        expected_doc = MagicMock(spec=DocumentRecord)
        repo.find_one = AsyncMock(return_value=expected_doc)

        result = await repo.get_by_thread_id_and_user("thread-abc", user_id)

        assert result is expected_doc
        repo.find_one.assert_called_once_with(
            {"thread_id": "thread-abc", "user_id": user_id}
        )

    async def test_returns_none_when_thread_exists_but_user_does_not_match(
        self, repo: DocumentRepository
    ) -> None:
        """Returns None when thread_id exists but belongs to a different user."""
        user_id = PydanticObjectId()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_thread_id_and_user("thread-abc", user_id)

        assert result is None
        repo.find_one.assert_called_once_with(
            {"thread_id": "thread-abc", "user_id": user_id}
        )

    async def test_returns_none_when_thread_does_not_exist(
        self, repo: DocumentRepository
    ) -> None:
        """Returns None when thread_id does not exist at all."""
        user_id = PydanticObjectId()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_thread_id_and_user("nonexistent", user_id)

        assert result is None
        repo.find_one.assert_called_once_with(
            {"thread_id": "nonexistent", "user_id": user_id}
        )


class TestGetByThreadId:
    """Tests for DocumentRepository.get_by_thread_id()."""

    @pytest.fixture()
    def repo(self) -> DocumentRepository:
        return DocumentRepository()

    async def test_returns_document_when_thread_exists(
        self, repo: DocumentRepository
    ) -> None:
        """Returns DocumentRecord when thread_id exists."""
        expected_doc = MagicMock(spec=DocumentRecord)
        repo.find_one = AsyncMock(return_value=expected_doc)

        result = await repo.get_by_thread_id("thread-abc")

        assert result is expected_doc
        repo.find_one.assert_called_once_with({"thread_id": "thread-abc"})

    async def test_returns_none_when_thread_does_not_exist(
        self, repo: DocumentRepository
    ) -> None:
        """Returns None when thread_id does not exist."""
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_thread_id("nonexistent")

        assert result is None
        repo.find_one.assert_called_once_with({"thread_id": "nonexistent"})


class TestDocumentRecordVersionIndex:
    """Verify the unique compound index on (application_id, doc_type, version)."""

    def test_unique_compound_index_exists(self) -> None:
        """AC #2: unique compound index must exist in DocumentRecord.Settings.indexes."""
        for idx in DocumentRecord.Settings.indexes:
            if idx.document.get("name") == "application_doctype_version_uidx":
                assert idx.document.get("unique") is True
                # Verify the index covers the right fields
                keys = idx.document.get("key")
                field_names = list(keys)
                assert "application_id" in field_names
                assert "doc_type" in field_names
                assert "version" in field_names
                return
        pytest.fail("application_doctype_version_uidx not found in DocumentRecord.Settings.indexes")

    def test_existing_indexes_preserved(self) -> None:
        """Existing indexes must not be removed when adding the new one."""
        index_names = [
            idx.document.get("name") for idx in DocumentRecord.Settings.indexes
        ]
        assert "user_doctype_idx" in index_names
        assert "application_doctype_idx" in index_names


# ---------------------------------------------------------------------------
# Task 2 & 3: create_versioned() tests
# ---------------------------------------------------------------------------


class TestCreateVersioned:
    """Tests for DocumentRepository.create_versioned() atomic version assignment."""

    @pytest.fixture()
    def repo(self) -> DocumentRepository:
        return DocumentRepository()

    @pytest.fixture()
    def mock_doc(self) -> MagicMock:
        doc = MagicMock(spec=DocumentRecord)
        doc.application_id = PydanticObjectId()
        doc.doc_type = DocumentType.COVER_LETTER
        doc.version = 1
        doc.insert = AsyncMock()
        return doc

    async def test_create_versioned_succeeds_on_first_attempt(
        self, repo: DocumentRepository, mock_doc: MagicMock
    ) -> None:
        """Happy path: insert succeeds on first try with correct version."""
        repo._get_next_version = AsyncMock(return_value=1)

        result = await repo.create_versioned(mock_doc)

        assert result is mock_doc
        assert mock_doc.version == 1
        mock_doc.insert.assert_called_once()
        repo._get_next_version.assert_called_once_with(
            mock_doc.application_id, mock_doc.doc_type
        )

    async def test_create_versioned_retries_on_duplicate_key(
        self, repo: DocumentRepository, mock_doc: MagicMock
    ) -> None:
        """AC #1: retries with incremented version when DuplicateKeyError occurs."""
        mock_doc.insert = AsyncMock(
            side_effect=[DuplicateKeyError("dup key"), None]
        )
        repo._get_next_version = AsyncMock(side_effect=[1, 2])

        result = await repo.create_versioned(mock_doc)

        assert result is mock_doc
        assert mock_doc.version == 2
        assert mock_doc.insert.call_count == 2
        assert repo._get_next_version.call_count == 2

    async def test_create_versioned_raises_conflict_after_max_retries(
        self, repo: DocumentRepository, mock_doc: MagicMock
    ) -> None:
        """AC #3: raises ConflictError with DOCUMENT_VERSION_CONFLICT after retries exhausted."""
        mock_doc.insert = AsyncMock(
            side_effect=DuplicateKeyError("dup key")
        )
        repo._get_next_version = AsyncMock(side_effect=[1, 2, 3])

        with pytest.raises(ConflictError) as exc_info:
            await repo.create_versioned(mock_doc, max_retries=3)

        assert exc_info.value.error_code == "DOCUMENT_VERSION_CONFLICT"
        assert exc_info.value.status_code == 409
        assert mock_doc.insert.call_count == 3

    async def test_create_versioned_does_not_catch_non_duplicate_errors(
        self, repo: DocumentRepository, mock_doc: MagicMock
    ) -> None:
        """Non-DuplicateKeyError exceptions should propagate, not be caught."""
        mock_doc.insert = AsyncMock(side_effect=RuntimeError("connection lost"))
        repo._get_next_version = AsyncMock(return_value=1)

        with pytest.raises(RuntimeError, match="connection lost"):
            await repo.create_versioned(mock_doc)

    async def test_create_versioned_logs_retry_attempts(
        self, repo: DocumentRepository, mock_doc: MagicMock
    ) -> None:
        """Retry attempts should be logged with structlog."""
        mock_doc.insert = AsyncMock(
            side_effect=[DuplicateKeyError("dup key"), None]
        )
        repo._get_next_version = AsyncMock(side_effect=[1, 2])

        with patch("src.repositories.document_repository.logger") as mock_logger:
            await repo.create_versioned(mock_doc)
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            # Verify structured log contains relevant context fields
            assert call_kwargs["application_id"] == str(mock_doc.application_id)
            assert call_kwargs["doc_type"] == mock_doc.doc_type
            assert call_kwargs["attempt"] == 1


# ---------------------------------------------------------------------------
# Task 4.5 & 4.6: API-level conflict tests
# ---------------------------------------------------------------------------


class TestStartCoverLetterVersionConflict:
    """Verify start_cover_letter returns 409 on version conflict, not raw 500."""

    async def test_start_cover_letter_version_conflict_returns_409(
        self, client
    ) -> None:
        """AC #3: version conflict surfaces as 409 DOCUMENT_VERSION_CONFLICT."""
        from src.api.dependencies import (
            get_application_repository,
            get_current_user,
            get_document_repository,
            get_job_repository,
            get_resume_repository,
        )

        app = client.app  # type: ignore[attr-defined]

        fake_user = MagicMock()
        fake_user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        fake_user.email = "test@example.com"

        fake_application = MagicMock()
        fake_application.id = PydanticObjectId("222222222222222222222222")
        fake_application.user_id = fake_user.id
        fake_application.job_id = PydanticObjectId("111111111111111111111111")

        fake_job = MagicMock()
        fake_job.id = PydanticObjectId("111111111111111111111111")
        fake_job.title = "Engineer"
        fake_job.company_name = "Acme"
        fake_job.description = "Build things"

        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = fake_application

        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = fake_job

        mock_doc_repo = AsyncMock()
        mock_doc_repo.create_versioned = AsyncMock(
            side_effect=ConflictError(
                detail="Document version conflict",
                error_code="DOCUMENT_VERSION_CONFLICT",
            )
        )
        mock_doc_repo.get_in_progress_for_application = AsyncMock(return_value=None)

        mock_resume_repo = AsyncMock()
        mock_llm_usage_repo = AsyncMock()
        mock_llm_usage_repo.count_recent_for_user = AsyncMock(return_value=0)

        from src.api.dependencies import get_llm_usage_repository

        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
        app.dependency_overrides[get_llm_usage_repository] = lambda: mock_llm_usage_repo

        try:
            response = await client.post(
                "/apply/applications/222222222222222222222222/cover-letter",
                json={},
            )
            assert response.status_code == 409
            data = response.json()
            assert data["error_code"] == "DOCUMENT_VERSION_CONFLICT"
        finally:
            app.dependency_overrides.clear()

    async def test_delete_for_application_delegates_to_delete_many(self) -> None:
        """delete_for_application() calls delete_many with correct filter."""
        repo = DocumentRepository()
        app_id = PydanticObjectId()
        repo.delete_many = AsyncMock(return_value=3)

        result = await repo.delete_for_application(app_id)

        assert result == 3
        repo.delete_many.assert_called_once_with({"application_id": app_id})

    async def test_delete_for_application_returns_zero_when_no_docs(self) -> None:
        """delete_for_application() returns 0 when no matching documents exist."""
        repo = DocumentRepository()
        app_id = PydanticObjectId()
        repo.delete_many = AsyncMock(return_value=0)

        result = await repo.delete_for_application(app_id)

        assert result == 0
        repo.delete_many.assert_called_once_with({"application_id": app_id})


# ---------------------------------------------------------------------------
# Story 3.3: get_in_progress_for_application tests
# ---------------------------------------------------------------------------


async def test_get_in_progress_for_application_delegates_to_find_one():
    """get_in_progress_for_application calls find_one with correct filter."""
    repo = DocumentRepository()
    app_id = PydanticObjectId("222222222222222222222222")
    fake_doc = MagicMock()
    repo.find_one = AsyncMock(return_value=fake_doc)

    result = await repo.get_in_progress_for_application(
        app_id, DocumentType.COVER_LETTER
    )

    assert result is fake_doc
    repo.find_one.assert_called_once_with(
        {
            "application_id": app_id,
            "doc_type": DocumentType.COVER_LETTER,
            "thread_id": {"$ne": ""},
            "content": "",
            "is_approved": False,
        }
    )


async def test_get_in_progress_for_application_returns_none():
    """get_in_progress_for_application returns None when no in-progress doc."""
    repo = DocumentRepository()
    app_id = PydanticObjectId("222222222222222222222222")
    repo.find_one = AsyncMock(return_value=None)

    result = await repo.get_in_progress_for_application(
        app_id, DocumentType.COVER_LETTER
    )

    assert result is None

    async def test_create_versioned_restores_version_on_failure(self) -> None:
        """Document.version is restored to its original value when all retries exhaust."""
        repo = DocumentRepository()
        mock_doc = MagicMock(spec=DocumentRecord)
        mock_doc.application_id = PydanticObjectId()
        mock_doc.doc_type = DocumentType.COVER_LETTER
        mock_doc.version = 1  # original value

        mock_doc.insert = AsyncMock(side_effect=DuplicateKeyError("dup key"))
        repo._get_next_version = AsyncMock(side_effect=[5, 6, 7])

        with pytest.raises(ConflictError):
            await repo.create_versioned(mock_doc, max_retries=3)

        # version must be restored, not left at the last failed attempt (7)
        assert mock_doc.version == 1
