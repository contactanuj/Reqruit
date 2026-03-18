"""
Unit tests for profile and resume management routes.

Follows the dependency_overrides pattern: all repositories and get_current_user
are replaced with lambdas returning mock instances. No database calls are made.

Why client.app (not `from src.api.main import app`):
    The `client` fixture calls create_app() which creates a fresh FastAPI
    instance. The module-level `app = create_app()` in main.py is a separate
    singleton created at import time. Setting dependency_overrides on the
    module-level app has no effect on the client's app instance.
    `client.app` is set by the conftest fixture to the correct instance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_profile_repository,
    get_resume_repository,
)
from src.db.documents.profile import Profile, UserPreferences
from src.db.documents.resume import Resume

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_profile(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    profile = MagicMock(spec=Profile)
    profile.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    profile.user_id = PydanticObjectId(user_id)
    profile.full_name = "Test User"
    profile.headline = "Engineer"
    profile.summary = "Summary"
    profile.skills = ["python"]
    profile.target_roles = ["Engineer"]
    profile.years_of_experience = 5
    profile.preferences = UserPreferences()
    profile.updated_at = None
    return profile


def _make_resume(user_id: str = "aaaaaaaaaaaaaaaaaaaaaaaa"):
    resume = MagicMock(spec=Resume)
    resume.id = PydanticObjectId("cccccccccccccccccccccccc")
    resume.user_id = PydanticObjectId(user_id)
    resume.title = "My Resume"
    resume.file_name = "resume.pdf"
    resume.version = 1
    resume.is_master = False
    resume.raw_text = "raw text"
    resume.parsed_data = None
    resume.parse_status = "pending"
    resume.created_at = None
    return resume


# ---------------------------------------------------------------------------
# Tests: GET /profile
# ---------------------------------------------------------------------------


async def test_get_profile_returns_200(client: AsyncClient) -> None:
    """GET /profile should return 200 and auto-create profile."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_profile = _make_profile()

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_or_create.return_value = fake_profile

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_profile_repository] = lambda: mock_profile_repo

    try:
        response = await client.get("/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test User"
        assert data["headline"] == "Engineer"
        assert "id" in data
    finally:
        app.dependency_overrides.clear()


async def test_get_profile_requires_auth(client: AsyncClient) -> None:
    """GET /profile without token should return 401 or 403."""
    response = await client.get("/profile")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests: PATCH /profile
# ---------------------------------------------------------------------------


async def test_patch_profile_updates_fields(client: AsyncClient) -> None:
    """PATCH /profile should update specified fields only."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_profile = _make_profile()
    updated_profile = _make_profile()
    updated_profile.full_name = "Updated Name"

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_or_create.return_value = fake_profile
    mock_profile_repo.update.return_value = updated_profile

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_profile_repository] = lambda: mock_profile_repo

    try:
        response = await client.patch("/profile", json={"full_name": "Updated Name"})
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        mock_profile_repo.update.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_patch_profile_empty_body_no_update(client: AsyncClient) -> None:
    """PATCH /profile with empty body should not call update."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_profile = _make_profile()

    mock_profile_repo = AsyncMock()
    mock_profile_repo.get_or_create.return_value = fake_profile

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_profile_repository] = lambda: mock_profile_repo

    try:
        response = await client.patch("/profile", json={})
        assert response.status_code == 200
        mock_profile_repo.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /profile/resumes
# ---------------------------------------------------------------------------


async def test_list_resumes_returns_list(client: AsyncClient) -> None:
    """GET /profile/resumes should return a list of resume summaries."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_resume = _make_resume()

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_all_for_user.return_value = [fake_resume]

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.get("/profile/resumes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "My Resume"
        assert data[0]["parse_status"] == "pending"
    finally:
        app.dependency_overrides.clear()


async def test_list_resumes_empty(client: AsyncClient) -> None:
    """GET /profile/resumes returns empty list when no resumes exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_all_for_user.return_value = []

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.get("/profile/resumes")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /profile/resumes/{id}
# ---------------------------------------------------------------------------


async def test_get_resume_returns_detail(client: AsyncClient) -> None:
    """GET /profile/resumes/{id} returns full resume detail for the owner."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    fake_user = _make_user(user_id)
    fake_resume = _make_resume(user_id)

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_id.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.get(f"/profile/resumes/{fake_resume.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["raw_text"] == "raw text"
        assert data["parsed_data"] is None
    finally:
        app.dependency_overrides.clear()


async def test_get_resume_404_for_nonexistent(client: AsyncClient) -> None:
    """GET /profile/resumes/{id} returns 404 when resume does not exist."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_id.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.get("/profile/resumes/aaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 404
        assert response.json()["error_code"] == "RESUME_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_get_resume_403_for_wrong_user(client: AsyncClient) -> None:
    """GET /profile/resumes/{id} returns 403 when resume belongs to another user."""
    app = client.app  # type: ignore[attr-defined]

    # Current user is "aaaa...", but resume belongs to "bbbb..."
    fake_user = _make_user("aaaaaaaaaaaaaaaaaaaaaaaa")
    fake_resume = _make_resume("bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_id.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.get(f"/profile/resumes/{fake_resume.id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: DELETE /profile/resumes/{id}
# ---------------------------------------------------------------------------


async def test_delete_resume_returns_204(client: AsyncClient) -> None:
    """DELETE /profile/resumes/{id} returns 204 for the owner."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    fake_user = _make_user(user_id)
    fake_resume = _make_resume(user_id)

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_id.return_value = fake_resume
    mock_resume_repo.delete.return_value = True

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.delete(f"/profile/resumes/{fake_resume.id}")
        assert response.status_code == 204
        mock_resume_repo.delete.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_delete_resume_403_for_wrong_user(client: AsyncClient) -> None:
    """DELETE /profile/resumes/{id} returns 403 when resume belongs to another user."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user("aaaaaaaaaaaaaaaaaaaaaaaa")
    fake_resume = _make_resume("bbbbbbbbbbbbbbbbbbbbbbbb")

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_id.return_value = fake_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.delete(f"/profile/resumes/{fake_resume.id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /profile/resumes/upload
# ---------------------------------------------------------------------------


async def test_upload_resume_passes_user_id_to_background_task(
    client: AsyncClient,
) -> None:
    """Upload should pass str(current_user.id) as third arg to background task."""
    app = client.app  # type: ignore[attr-defined]

    user_id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    fake_user = _make_user(user_id)

    mock_resume_repo = AsyncMock()
    mock_resume_repo.count_for_user.return_value = 0
    created_resume = _make_resume(user_id)
    mock_resume_repo.create.return_value = created_resume

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        with (
            patch(
                "src.api.routes.profile._parse_resume_background"
            ) as mock_bg,
            patch(
                "src.api.routes.profile._extract_text", return_value="some text"
            ),
        ):
            response = await client.post(
                "/profile/resumes/upload",
                files={"file": ("resume.pdf", b"%PDF-fake", "application/pdf")},
            )
            assert response.status_code == 202

            # Background task should receive user_id as third argument
            mock_bg.assert_called_once()
            call_args = mock_bg.call_args[0]
            assert call_args[2] == str(fake_user.id)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /profile/resumes/{id}/reparse (Story 3.4)
# ---------------------------------------------------------------------------


async def test_reparse_failed_resume_returns_202(client: AsyncClient) -> None:
    """POST reparse with parse_status='failed' returns 202 and queues background task."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_resume = _make_resume()
    fake_resume.parse_status = "failed"

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=fake_resume)
    mock_resume_repo.update = AsyncMock(return_value=fake_resume)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        with patch("src.api.routes.profile._parse_resume_background") as mock_bg:
            response = await client.post(
                f"/profile/resumes/{fake_resume.id}/reparse",
            )
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "reparse_queued"
            mock_resume_repo.update.assert_called_once()
            mock_bg.assert_called_once()
    finally:
        app.dependency_overrides.clear()


async def test_reparse_completed_resume_returns_422(client: AsyncClient) -> None:
    """POST reparse with parse_status='completed' returns 422 INVALID_STATUS_TRANSITION."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_resume = _make_resume()
    fake_resume.parse_status = "completed"

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=fake_resume)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.post(
            f"/profile/resumes/{fake_resume.id}/reparse",
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_STATUS_TRANSITION"
    finally:
        app.dependency_overrides.clear()


async def test_reparse_processing_resume_returns_422(client: AsyncClient) -> None:
    """POST reparse with parse_status='processing' returns 422."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_resume = _make_resume()
    fake_resume.parse_status = "processing"

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=fake_resume)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.post(
            f"/profile/resumes/{fake_resume.id}/reparse",
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_STATUS_TRANSITION"
    finally:
        app.dependency_overrides.clear()


async def test_reparse_pending_resume_returns_422(client: AsyncClient) -> None:
    """POST reparse with parse_status='pending' returns 422."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()
    fake_resume = _make_resume()
    fake_resume.parse_status = "pending"

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=fake_resume)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.post(
            f"/profile/resumes/{fake_resume.id}/reparse",
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_STATUS_TRANSITION"
    finally:
        app.dependency_overrides.clear()


async def test_reparse_nonexistent_resume_returns_404(client: AsyncClient) -> None:
    """POST reparse with non-existent resume returns 404."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user()

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.post(
            "/profile/resumes/aaaaaaaaaaaaaaaaaaaaaaaa/reparse",
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "RESUME_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_reparse_wrong_user_returns_404(client: AsyncClient) -> None:
    """POST reparse with resume belonging to different user returns 404."""
    app = client.app  # type: ignore[attr-defined]

    fake_user = _make_user("aaaaaaaaaaaaaaaaaaaaaaaa")

    mock_resume_repo = AsyncMock()
    mock_resume_repo.get_by_user_and_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo

    try:
        response = await client.post(
            "/profile/resumes/cccccccccccccccccccccccc/reparse",
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
