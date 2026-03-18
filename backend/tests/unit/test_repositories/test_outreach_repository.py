"""
Unit tests for OutreachMessageRepository.

Coverage:
- get_by_user_and_id builds correct filter
- get_for_application builds correct filter
- get_for_user builds correct filter
"""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.repositories.outreach_repository import OutreachMessageRepository


def _make_repo() -> OutreachMessageRepository:
    repo = OutreachMessageRepository.__new__(OutreachMessageRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestGetByUserAndId:
    async def test_passes_correct_filter(self):
        repo = _make_repo()
        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        msg_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        await repo.get_by_user_and_id(user_id, msg_id)
        repo.find_one.assert_called_once_with(
            {"_id": msg_id, "user_id": user_id}
        )


class TestGetForApplication:
    async def test_passes_correct_filter_and_sort(self):
        repo = _make_repo()
        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        app_id = PydanticObjectId("cccccccccccccccccccccccc")
        await repo.get_for_application(user_id, app_id, skip=5, limit=10)
        repo.find_many.assert_called_once_with(
            {"user_id": user_id, "application_id": app_id},
            skip=5,
            limit=10,
            sort="-created_at",
        )


class TestGetForUser:
    async def test_passes_correct_filter(self):
        repo = _make_repo()
        user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
        await repo.get_for_user(user_id, skip=0, limit=50)
        repo.find_many.assert_called_once_with(
            {"user_id": user_id},
            skip=0,
            limit=50,
            sort="-created_at",
        )
