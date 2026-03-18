"""
Tests for STAR story CRUD endpoints.

Story 5.1: STAR Story CRUD — create, list, get, update, delete.

Coverage:
- POST /interviews/star-stories creates with correct user_id (201)
- POST /interviews/star-stories with missing title returns 422
- GET /interviews/star-stories returns only user's stories
- GET /interviews/star-stories returns empty list when none exist
- GET /interviews/star-stories/{id} returns 404 for non-existent
- GET /interviews/star-stories/{id} returns 404 for other user's story
- PUT /interviews/star-stories/{id} updates and returns updated story
- PUT /interviews/star-stories/{id} returns 404 for non-existent
- DELETE /interviews/star-stories/{id} returns 204
- DELETE /interviews/star-stories/{id} returns 404 for non-existent
- All endpoints return 401 without auth token
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_star_story_repository
from src.db.documents.star_story import STARStory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
STORY_ID = "bbbbbbbbbbbbbbbbbbbbbbbb"


def _make_user(user_id: str = USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_story(
    story_id: str = STORY_ID,
    user_id: str = USER_ID,
    title: str = "Led DB migration",
):
    story = MagicMock(spec=STARStory)
    story.id = PydanticObjectId(story_id)
    story.user_id = PydanticObjectId(user_id)
    story.title = title
    story.situation = "Legacy MySQL system was slow"
    story.task = "Migrate to PostgreSQL"
    story.action = "Designed phased migration"
    story.result = "Zero downtime, 40% improvement"
    story.tags = ["leadership", "databases"]
    story.created_at = None
    story.updated_at = None
    return story


def _setup(app, mock_repo, fake_user=None):
    app.dependency_overrides[get_current_user] = lambda: (fake_user or _make_user())
    app.dependency_overrides[get_star_story_repository] = lambda: mock_repo


STORY_PAYLOAD = {
    "title": "Led DB migration",
    "situation": "Legacy MySQL system was slow",
    "task": "Migrate to PostgreSQL",
    "action": "Designed phased migration",
    "result": "Zero downtime, 40% improvement",
    "tags": ["leadership", "databases"],
}


# ---------------------------------------------------------------------------
# Tests: POST /interviews/star-stories
# ---------------------------------------------------------------------------


class TestCreateSTARStory:

    async def test_create_returns_201_with_correct_fields(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_user = _make_user()
        fake_story = _make_story()

        mock_repo = AsyncMock()
        mock_repo.create.return_value = fake_story
        _setup(app, mock_repo, fake_user)

        try:
            response = await client.post(
                "/interviews/star-stories", json=STORY_PAYLOAD
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == STORY_ID
            assert data["title"] == "Led DB migration"
            assert data["tags"] == ["leadership", "databases"]
            # Verify user_id was set from current_user, not request body
            create_arg = mock_repo.create.call_args.args[0]
            assert create_arg.user_id == fake_user.id
        finally:
            app.dependency_overrides.clear()

    async def test_create_missing_title_returns_422(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        _setup(app, mock_repo)

        try:
            response = await client.post(
                "/interviews/star-stories", json={"situation": "something"}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_create_returns_401_without_auth(self, client: AsyncClient):
        response = await client.post(
            "/interviews/star-stories", json=STORY_PAYLOAD
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interviews/star-stories
# ---------------------------------------------------------------------------


class TestListSTARStories:

    async def test_list_returns_users_stories(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_story = _make_story()

        mock_repo = AsyncMock()
        mock_repo.get_all_for_user.return_value = [fake_story]
        _setup(app, mock_repo)

        try:
            response = await client.get("/interviews/star-stories")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["title"] == "Led DB migration"
        finally:
            app.dependency_overrides.clear()

    async def test_list_empty_returns_empty_list(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        mock_repo.get_all_for_user.return_value = []
        _setup(app, mock_repo)

        try:
            response = await client.get("/interviews/star-stories")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_list_returns_401_without_auth(self, client: AsyncClient):
        response = await client.get("/interviews/star-stories")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /interviews/star-stories/{id}
# ---------------------------------------------------------------------------


class TestGetSTARStory:

    async def test_get_returns_story(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_story = _make_story()

        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = fake_story
        _setup(app, mock_repo)

        try:
            response = await client.get(f"/interviews/star-stories/{STORY_ID}")
            assert response.status_code == 200
            assert response.json()["id"] == STORY_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_repo)

        try:
            response = await client.get(f"/interviews/star-stories/{STORY_ID}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_get_other_users_story_returns_404(self, client: AsyncClient):
        """Owner scoping: get_by_user_and_id returns None for other user's story."""
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_repo)

        try:
            response = await client.get(f"/interviews/star-stories/{STORY_ID}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_get_returns_401_without_auth(self, client: AsyncClient):
        response = await client.get(f"/interviews/star-stories/{STORY_ID}")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: PUT /interviews/star-stories/{id}
# ---------------------------------------------------------------------------


class TestUpdateSTARStory:

    async def test_update_returns_updated_story(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_story = _make_story()
        updated_story = _make_story(title="Updated title")

        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = fake_story
        mock_repo.update.return_value = updated_story
        _setup(app, mock_repo)

        try:
            response = await client.patch(
                f"/interviews/star-stories/{STORY_ID}",
                json={"title": "Updated title"},
            )
            assert response.status_code == 200
            assert response.json()["title"] == "Updated title"
            mock_repo.update.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_update_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_repo)

        try:
            response = await client.patch(
                f"/interviews/star-stories/{STORY_ID}",
                json={"title": "Updated title"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_update_returns_401_without_auth(self, client: AsyncClient):
        response = await client.patch(
            f"/interviews/star-stories/{STORY_ID}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: DELETE /interviews/star-stories/{id}
# ---------------------------------------------------------------------------


class TestDeleteSTARStory:

    async def test_delete_returns_204(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        fake_story = _make_story()

        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = fake_story
        mock_repo.delete.return_value = None
        _setup(app, mock_repo)

        try:
            response = await client.delete(f"/interviews/star-stories/{STORY_ID}")
            assert response.status_code == 204
            assert response.content == b""
            mock_repo.delete.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_repo = AsyncMock()
        mock_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_repo)

        try:
            response = await client.delete(f"/interviews/star-stories/{STORY_ID}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_delete_returns_401_without_auth(self, client: AsyncClient):
        response = await client.delete(f"/interviews/star-stories/{STORY_ID}")
        assert response.status_code == 401
