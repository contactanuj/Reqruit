"""
Unit tests for MockSessionRepository.

Coverage:
- get_by_user_and_id builds correct filter
- get_for_interview builds correct filter with sort
"""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.repositories.mock_session_repository import MockSessionRepository


def _make_repo() -> MockSessionRepository:
    repo = MockSessionRepository.__new__(MockSessionRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestGetByUserAndId:
    async def test_passes_correct_filter(self):
        repo = _make_repo()
        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        session_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        await repo.get_by_user_and_id(user_id, session_id)
        repo.find_one.assert_called_once_with(
            {"_id": session_id, "user_id": user_id}
        )


class TestGetForInterview:
    async def test_passes_correct_filter_and_sort(self):
        repo = _make_repo()
        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        interview_id = PydanticObjectId("cccccccccccccccccccccccc")
        await repo.get_for_interview(user_id, interview_id, skip=5, limit=10)
        repo.find_many.assert_called_once_with(
            {"user_id": user_id, "interview_id": interview_id},
            skip=5,
            limit=10,
            sort="-created_at",
        )
