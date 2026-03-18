"""
Tests for STARStoryRepository owner-scoped methods.

Verifies that repository methods pass correct filters to BaseRepository.
"""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.repositories.star_story_repository import STARStoryRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
STORY_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_repo():
    repo = STARStoryRepository.__new__(STARStoryRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestGetByUserAndId:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.get_by_user_and_id(USER_ID, STORY_ID)
        repo.find_one.assert_called_once_with({"_id": STORY_ID, "user_id": USER_ID})


class TestGetAllForUser:

    async def test_passes_correct_filter_and_sort(self):
        repo = _make_repo()
        await repo.get_all_for_user(USER_ID, skip=5, limit=10)
        repo.find_many.assert_called_once_with(
            {"user_id": USER_ID}, skip=5, limit=10, sort="-created_at"
        )


class TestGetByTags:

    async def test_passes_in_filter(self):
        repo = _make_repo()
        await repo.get_by_tags(USER_ID, ["leadership", "databases"])
        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == USER_ID
        assert set(filters["tags"]["$in"]) == {"leadership", "databases"}
