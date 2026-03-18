"""
Tests for InterviewRepository owner-scoped methods.

Verifies that repository methods pass correct filters to BaseRepository.
"""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.repositories.interview_repository import InterviewRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
INTERVIEW_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
APP_ID = PydanticObjectId("cccccccccccccccccccccccc")


def _make_repo():
    repo = InterviewRepository.__new__(InterviewRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestGetByUserAndId:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.get_by_user_and_id(USER_ID, INTERVIEW_ID)
        repo.find_one.assert_called_once_with(
            {"_id": INTERVIEW_ID, "user_id": USER_ID}
        )


class TestGetForUser:

    async def test_without_application_filter(self):
        repo = _make_repo()
        await repo.get_for_user(USER_ID, skip=5, limit=10)
        call_args = repo.find_many.call_args
        assert call_args.args[0] == {"user_id": USER_ID}
        assert call_args.kwargs["skip"] == 5
        assert call_args.kwargs["limit"] == 10
        assert call_args.kwargs["sort"] == "scheduled_at"

    async def test_with_application_filter(self):
        repo = _make_repo()
        await repo.get_for_user(USER_ID, application_id=APP_ID)
        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == USER_ID
        assert filters["application_id"] == APP_ID


class TestGetForApplication:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.get_for_application(USER_ID, APP_ID)
        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == USER_ID
        assert filters["application_id"] == APP_ID
        assert call_args.kwargs["sort"] == "scheduled_at"
