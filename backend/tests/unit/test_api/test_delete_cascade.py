"""
Unit tests for DELETE /jobs/{id} cascade deletion.

Verifies that deleting a job cascade-deletes all associated data:
DocumentRecords, OutreachMessages, Interviews, the Application,
Weaviate embeddings (JobEmbedding + CoverLetterEmbedding), and the Job.

Weaviate failures are non-blocking (logged as warnings, never fail the request).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
from src.db.documents.enums import ApplicationStatus, DocumentType
from src.db.documents.job import Job, JobRequirements


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    return user


def _make_job(job_id: str = "111111111111111111111111"):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Staff Engineer"
    job.company_name = "Acme Corp"
    job.requirements = JobRequirements(required_skills=[], preferred_skills=[])
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
    return app


def _make_document(doc_id: str, doc_type: DocumentType):
    doc = MagicMock()
    doc.id = PydanticObjectId(doc_id)
    doc.doc_type = doc_type
    return doc


# ---------------------------------------------------------------------------
# Tests: Full cascade DELETE /jobs/{id}
# ---------------------------------------------------------------------------


async def test_delete_job_cascades_all_associated_data(client: AsyncClient) -> None:
    """[AC #1] Full cascade: docs, outreach, interviews, Weaviate, app, job all deleted."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    # Documents: one cover letter and one tailored resume
    fake_docs = [
        _make_document("333333333333333333333333", DocumentType.COVER_LETTER),
        _make_document("444444444444444444444444", DocumentType.TAILORED_RESUME),
    ]

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.return_value = True

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.return_value = True

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = fake_docs
    mock_doc_repo.delete_for_application.return_value = 2

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.return_value = 1

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.return_value = 3

    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_cover_letter_embeddings_for_docs.return_value = 1
    mock_indexing_service.delete_job_embeddings.return_value = 1

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        assert response.status_code == 204

        # Verify doc IDs fetched before deletion
        mock_doc_repo.get_for_application.assert_called_once_with(fake_application.id)

        # Verify Weaviate cover letter cleanup called with only the cover letter doc ID
        mock_indexing_service.delete_cover_letter_embeddings_for_docs.assert_called_once_with(
            ["333333333333333333333333"], str(fake_user.id)
        )

        # Verify MongoDB cascade deletes
        mock_doc_repo.delete_for_application.assert_called_once_with(fake_application.id)
        mock_outreach_repo.delete_many.assert_called_once_with(
            {"application_id": fake_application.id}
        )
        mock_interview_repo.delete_many.assert_called_once_with(
            {"application_id": fake_application.id}
        )
        mock_app_repo.delete.assert_called_once_with(fake_application.id)

        # Verify Weaviate job embedding cleanup
        mock_indexing_service.delete_job_embeddings.assert_called_once_with(
            str(fake_job.id), str(fake_user.id)
        )

        # Verify job itself deleted
        mock_job_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_no_applications_returns_403(client: AsyncClient) -> None:
    """[AC ownership] 403 when user has no application for the job."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.delete(f"/jobs/{job_id}")
        assert response.status_code == 403
        assert response.json()["error_code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_no_children_idempotent(client: AsyncClient) -> None:
    """[AC #3] Cascade succeeds when application has no docs, outreach, or interviews."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.return_value = True

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.return_value = True

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = []  # no documents
    mock_doc_repo.delete_for_application.return_value = 0

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.return_value = 0

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.return_value = 0

    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_job_embeddings.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        assert response.status_code == 204

        # Cover letter embedding cleanup NOT called (no docs)
        mock_indexing_service.delete_cover_letter_embeddings_for_docs.assert_not_called()

        # All cascade deletes still called (idempotent — return 0)
        mock_doc_repo.delete_for_application.assert_called_once_with(fake_application.id)
        mock_outreach_repo.delete_many.assert_called_once()
        mock_interview_repo.delete_many.assert_called_once()
        mock_app_repo.delete.assert_called_once_with(fake_application.id)
        mock_job_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_weaviate_job_embedding_failure_nonblocking(
    client: AsyncClient,
) -> None:
    """[AC #2] Weaviate JobEmbedding failure is logged, MongoDB deletes still proceed."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

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

    # Weaviate delete raises an exception
    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_job_embeddings.side_effect = Exception("Weaviate down")

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        # Request still succeeds despite Weaviate failure
        assert response.status_code == 204

        # MongoDB deletes still completed
        mock_app_repo.delete.assert_called_once_with(fake_application.id)
        mock_job_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_weaviate_cover_letter_failure_nonblocking(
    client: AsyncClient,
) -> None:
    """[AC #2] Weaviate CoverLetterEmbedding failure is logged, MongoDB deletes still proceed."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    fake_docs = [
        _make_document("333333333333333333333333", DocumentType.COVER_LETTER),
    ]

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.return_value = True

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.return_value = True

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = fake_docs
    mock_doc_repo.delete_for_application.return_value = 1

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.return_value = 0

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.return_value = 0

    # Cover letter Weaviate delete raises
    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_cover_letter_embeddings_for_docs.side_effect = Exception(
        "Weaviate tenant missing"
    )
    mock_indexing_service.delete_job_embeddings.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        # Request succeeds despite cover letter Weaviate failure
        assert response.status_code == 204

        # MongoDB cascade still completed
        mock_doc_repo.delete_for_application.assert_called_once_with(fake_application.id)
        mock_outreach_repo.delete_many.assert_called_once()
        mock_interview_repo.delete_many.assert_called_once()
        mock_app_repo.delete.assert_called_once_with(fake_application.id)
        mock_job_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_404_not_found(client: AsyncClient) -> None:
    """DELETE /jobs/{id} returns 404 for non-existent job."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo

    try:
        response = await client.delete("/jobs/999999999999999999999999")
        assert response.status_code == 404
        assert response.json()["error_code"] == "JOB_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_only_cover_letters_trigger_weaviate_cleanup(
    client: AsyncClient,
) -> None:
    """Only cover letter documents trigger CoverLetterEmbedding cleanup, not other doc types."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    # Only a tailored resume — no cover letters
    fake_docs = [
        _make_document("444444444444444444444444", DocumentType.TAILORED_RESUME),
    ]

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.return_value = True

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.return_value = True

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = fake_docs
    mock_doc_repo.delete_for_application.return_value = 1

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.return_value = 0

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.return_value = 0

    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_job_embeddings.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        assert response.status_code == 204

        # No cover letters → cover letter embedding cleanup NOT called
        mock_indexing_service.delete_cover_letter_embeddings_for_docs.assert_not_called()

        # Job embedding cleanup still called
        mock_indexing_service.delete_job_embeddings.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_cascade_ordering(client: AsyncClient) -> None:
    """[AC #1] Cascade operations execute in correct order: cover letter embeddings →
    docs → outreach → interviews → application → job embeddings → job."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    fake_docs = [
        _make_document("333333333333333333333333", DocumentType.COVER_LETTER),
    ]

    # Track call ordering across all mocks via a shared list
    call_order: list[str] = []

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job
    mock_job_repo.delete.side_effect = lambda *a, **kw: call_order.append("job_delete")

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application
    mock_app_repo.delete.side_effect = lambda *a, **kw: call_order.append("app_delete")

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = fake_docs
    mock_doc_repo.delete_for_application.side_effect = lambda *a, **kw: (
        call_order.append("docs_delete") or 1
    )

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.side_effect = lambda *a, **kw: (
        call_order.append("outreach_delete") or 0
    )

    mock_interview_repo = AsyncMock()
    mock_interview_repo.delete_many.side_effect = lambda *a, **kw: (
        call_order.append("interviews_delete") or 0
    )

    mock_indexing_service = AsyncMock()
    mock_indexing_service.delete_cover_letter_embeddings_for_docs.side_effect = (
        lambda *a, **kw: call_order.append("cover_letter_embeddings_delete") or 1
    )
    mock_indexing_service.delete_job_embeddings.side_effect = (
        lambda *a, **kw: call_order.append("job_embeddings_delete") or 1
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_job_repository] = lambda: mock_job_repo
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    app.dependency_overrides[get_interview_repository] = lambda: mock_interview_repo

    try:
        with patch(
            "src.api.routes.jobs.build_indexing_service",
            return_value=mock_indexing_service,
        ):
            response = await client.delete(f"/jobs/{job_id}")

        assert response.status_code == 204

        # Verify exact ordering matches AC #1 cascade sequence
        assert call_order == [
            "cover_letter_embeddings_delete",
            "docs_delete",
            "outreach_delete",
            "interviews_delete",
            "app_delete",
            "job_embeddings_delete",
            "job_delete",
        ]
    finally:
        app.dependency_overrides.clear()


async def test_delete_job_partial_cascade_failure_propagates(
    client: AsyncClient,
) -> None:
    """[M4] If a MongoDB cascade step fails mid-way, the error propagates — documents
    deleted before the failure are NOT rolled back (known limitation, no transaction)."""
    app = client.app  # type: ignore[attr-defined]

    job_id = "111111111111111111111111"
    fake_user = _make_user()
    fake_job = _make_job(job_id)
    fake_application = _make_application()

    mock_job_repo = AsyncMock()
    mock_job_repo.get_by_id.return_value = fake_job

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_job_and_user.return_value = fake_application

    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_for_application.return_value = []
    mock_doc_repo.delete_for_application.return_value = 2  # succeeds

    mock_outreach_repo = AsyncMock()
    mock_outreach_repo.delete_many.side_effect = Exception("MongoDB connection lost")

    mock_interview_repo = AsyncMock()

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
            with pytest.raises(Exception, match="MongoDB connection lost"):
                await client.delete(f"/jobs/{job_id}")

        # Documents were already deleted before the failure (not rolled back)
        mock_doc_repo.delete_for_application.assert_called_once()

        # Interviews and job delete were never reached
        mock_interview_repo.delete_many.assert_not_called()
        mock_job_repo.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()
