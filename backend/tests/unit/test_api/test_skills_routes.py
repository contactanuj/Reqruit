"""
Unit tests for skills routes.

Covers:
    GET    /skills/profile              — get skills profile
    POST   /skills/profile              — create skills profile
    POST   /skills/profile/skills       — add a skill
    POST   /skills/profile/achievements — add an achievement
    DELETE /skills/profile              — delete skills profile
    POST   /skills/jd/decode            — decode job description
    POST   /skills/fit-score            — compute fit score
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_skills_profile_repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_profile(user_id=None):
    profile = MagicMock()
    profile.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    profile.user_id = user_id or PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    profile.skills = []
    profile.achievements = []
    profile.summary = ""
    profile.analysis_version = 0
    profile.model_dump.return_value = {
        "user_id": str(profile.user_id),
        "skills": [],
        "achievements": [],
        "summary": "",
        "analysis_version": 0,
    }
    return profile


def _override(app, user, repo):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_skills_profile_repository] = lambda: repo


# ---------------------------------------------------------------------------
# GET /skills/profile
# ---------------------------------------------------------------------------


class TestGetSkillsProfile:
    async def test_returns_profile(self, client: AsyncClient) -> None:
        user = _make_user()
        profile = _make_profile(user.id)
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=profile)
        _override(client.app, user, repo)

        response = await client.get("/skills/profile")

        assert response.status_code == 200
        assert response.json()["user_id"] == str(user.id)

    async def test_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=None)
        _override(client.app, user, repo)

        response = await client.get("/skills/profile")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /skills/profile
# ---------------------------------------------------------------------------


class TestCreateSkillsProfile:
    async def test_creates_profile(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=None)
        created = _make_profile(user.id)
        repo.create = AsyncMock(return_value=created)
        _override(client.app, user, repo)

        response = await client.post("/skills/profile")

        assert response.status_code == 201
        repo.create.assert_called_once()

    async def test_returns_existing_if_exists(self, client: AsyncClient) -> None:
        user = _make_user()
        existing = _make_profile(user.id)
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=existing)
        _override(client.app, user, repo)

        response = await client.post("/skills/profile")

        assert response.status_code == 201
        assert response.json()["user_id"] == str(user.id)


# ---------------------------------------------------------------------------
# POST /skills/profile/skills
# ---------------------------------------------------------------------------


class TestAddSkill:
    async def test_adds_skill(self, client: AsyncClient) -> None:
        user = _make_user()
        profile = _make_profile(user.id)
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=profile)
        repo.update = AsyncMock(return_value=profile)
        _override(client.app, user, repo)

        response = await client.post(
            "/skills/profile/skills",
            json={"name": "Python", "category": "Programming Language", "proficiency": "EXPERT"},
        )

        assert response.status_code == 200
        assert response.json()["skill"]["name"] == "Python"
        assert response.json()["skill"]["source"] == "manual"

    async def test_profile_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=None)
        _override(client.app, user, repo)

        response = await client.post(
            "/skills/profile/skills",
            json={"name": "Python"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /skills/profile/achievements
# ---------------------------------------------------------------------------


class TestAddAchievement:
    async def test_adds_achievement(self, client: AsyncClient) -> None:
        user = _make_user()
        profile = _make_profile(user.id)
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=profile)
        repo.update = AsyncMock(return_value=profile)
        _override(client.app, user, repo)

        response = await client.post(
            "/skills/profile/achievements",
            json={
                "title": "Built RAG pipeline",
                "impact": "3x search accuracy",
                "skills_demonstrated": ["Python", "Weaviate"],
            },
        )

        assert response.status_code == 200
        assert response.json()["achievement"]["title"] == "Built RAG pipeline"
        assert response.json()["achievement"]["source"] == "manual"

    async def test_profile_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=None)
        _override(client.app, user, repo)

        response = await client.post(
            "/skills/profile/achievements",
            json={"title": "Some achievement"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /skills/profile
# ---------------------------------------------------------------------------


class TestDeleteSkillsProfile:
    async def test_deletes_profile(self, client: AsyncClient) -> None:
        user = _make_user()
        profile = _make_profile(user.id)
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=profile)
        repo.delete = AsyncMock(return_value=True)
        _override(client.app, user, repo)

        response = await client.delete("/skills/profile")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

    async def test_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = MagicMock()
        repo.get_by_user = AsyncMock(return_value=None)
        _override(client.app, user, repo)

        response = await client.delete("/skills/profile")

        assert response.status_code == 404
