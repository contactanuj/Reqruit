"""
Unit tests for Stage 4 interview preparation routes (Stage 4: Prepare).

ALL TESTS IN THIS FILE ARE MARKED xfail(strict=False).

Implementation gap:
    The Interview document model exists at src/db/documents/interview.py
    and is registered in ALL_DOCUMENT_MODELS. However, no /prepare/* routes
    exist — prepare_router is not registered in src/api/main.py.

    Tests are marked xfail(strict=False) so they:
      - XFAIL today (expected failure, does not block CI)
      - Auto-XPASS once routes are implemented (no test changes needed)

Planned routes (to be implemented):
    GET    /prepare/applications/{application_id}/interviews
    POST   /prepare/applications/{application_id}/interviews
    GET    /prepare/applications/{application_id}/interviews/{interview_id}
    PATCH  /prepare/applications/{application_id}/interviews/{interview_id}/notes
    DELETE /prepare/applications/{application_id}/interviews/{interview_id}

Interview document (src/db/documents/interview.py):
    - application_id: PydanticObjectId
    - interview_type: str  (phone, technical, behavioral, panel, final)
    - questions: list[str]
    - preparation_notes: str
    - scheduled_at: datetime | None
    - InterviewNotes embedded
    Collection: interviews
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_current_user,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    return user


def _make_application(
    app_id: str = "222222222222222222222222",
    user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
):
    app = MagicMock()
    app.id = PydanticObjectId(app_id)
    app.user_id = PydanticObjectId(user_id)
    return app


def _make_interview(interview_id: str = "444444444444444444444444"):
    interview = MagicMock()
    interview.id = PydanticObjectId(interview_id)
    interview.application_id = PydanticObjectId("222222222222222222222222")
    interview.interview_type = "technical"
    interview.questions = ["Explain async/await", "Design a URL shortener"]
    interview.preparation_notes = "Review system design basics"
    interview.scheduled_at = None
    interview.created_at = None
    return interview


# ---------------------------------------------------------------------------
# Tests: Stage 4 routes (all xfail — routes not yet implemented)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_list_interviews_returns_empty_for_new_application(
    client: AsyncClient,
) -> None:
    """[P2] GET /prepare/applications/{id}/interviews returns [] for a new application."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(
            "/prepare/applications/222222222222222222222222/interviews"
        )
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_create_interview_returns_201_with_id(client: AsyncClient) -> None:
    """[P2] POST /prepare/applications/{id}/interviews creates an Interview, returns 201."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_interview = _make_interview()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.post(
            "/prepare/applications/222222222222222222222222/interviews",
            json={"interview_type": "technical", "scheduled_at": None},
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["interview_type"] == "technical"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_get_interview_returns_detail(client: AsyncClient) -> None:
    """[P2] GET /prepare/applications/{id}/interviews/{interview_id} returns full detail."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()
    fake_interview = _make_interview()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(
            "/prepare/applications/222222222222222222222222"
            "/interviews/444444444444444444444444"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interview_type"] == "technical"
        assert "questions" in data
        assert "preparation_notes" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_update_interview_notes_returns_200(client: AsyncClient) -> None:
    """[P2] PATCH .../interviews/{id}/notes updates preparation_notes, returns 200."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.patch(
            "/prepare/applications/222222222222222222222222"
            "/interviews/444444444444444444444444/notes",
            json={"preparation_notes": "Updated: study STAR method"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preparation_notes"] == "Updated: study STAR method"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_delete_interview_returns_204(client: AsyncClient) -> None:
    """[P2] DELETE .../interviews/{id} deletes the Interview, returns 204."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.delete(
            "/prepare/applications/222222222222222222222222"
            "/interviews/444444444444444444444444"
        )
        assert response.status_code == 204
    finally:
        app.dependency_overrides.clear()


@pytest.mark.xfail(
    strict=False,
    reason="Stage 4 not implemented: no /prepare/* routes registered in main.py",
)
async def test_get_interview_not_found_returns_404(client: AsyncClient) -> None:
    """[P2] GET interview with unknown id returns 404 INTERVIEW_NOT_FOUND."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_application = _make_application()

    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_id.return_value = fake_application

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_application_repository] = lambda: mock_app_repo

    try:
        response = await client.get(
            "/prepare/applications/222222222222222222222222"
            "/interviews/999999999999999999999999"
        )
        assert response.status_code == 404
        assert "NOT_FOUND" in response.json().get("error_code", "")
    finally:
        app.dependency_overrides.clear()
