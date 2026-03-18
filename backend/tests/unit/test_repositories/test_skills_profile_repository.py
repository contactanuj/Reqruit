"""Tests for SkillsProfileRepository."""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.db.documents.skills_profile import SkillsProfile
from src.repositories.skills_profile_repository import SkillsProfileRepository


class TestSkillsProfileRepository:
    """Tests for SkillsProfileRepository domain methods."""

    def test_init(self) -> None:
        repo = SkillsProfileRepository()
        assert repo._model is SkillsProfile

    async def test_get_by_user_found(self) -> None:
        repo = SkillsProfileRepository()
        user_id = PydanticObjectId()
        mock_profile = SkillsProfile(user_id=user_id)
        repo.find_one = AsyncMock(return_value=mock_profile)

        result = await repo.get_by_user(user_id)

        assert result is mock_profile
        repo.find_one.assert_called_once_with({"user_id": user_id})

    async def test_get_by_user_not_found(self) -> None:
        repo = SkillsProfileRepository()
        user_id = PydanticObjectId()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_user(user_id)

        assert result is None
        repo.find_one.assert_called_once_with({"user_id": user_id})

    async def test_inherits_base_repository_methods(self) -> None:
        repo = SkillsProfileRepository()
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "find_many")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "count")
