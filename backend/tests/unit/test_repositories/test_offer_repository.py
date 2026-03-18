"""
Tests for OfferRepository owner-scoped methods.

Verifies that repository methods pass correct filters to BaseRepository.
"""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.repositories.offer_repository import OfferRepository

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
OFFER_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
OFFER_ID_2 = PydanticObjectId("cccccccccccccccccccccccc")


def _make_repo():
    repo = OfferRepository.__new__(OfferRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestGetByUserAndId:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.get_by_user_and_id(USER_ID, OFFER_ID)
        repo.find_one.assert_called_once_with({"_id": OFFER_ID, "user_id": USER_ID})


class TestGetUserOffers:

    async def test_passes_correct_filter_and_sort(self):
        repo = _make_repo()
        await repo.get_user_offers(USER_ID)
        repo.find_many.assert_called_once_with(
            {"user_id": USER_ID}, skip=0, limit=100, sort="-created_at"
        )

    async def test_passes_pagination_params(self):
        repo = _make_repo()
        await repo.get_user_offers(USER_ID, skip=10, limit=5)
        repo.find_many.assert_called_once_with(
            {"user_id": USER_ID}, skip=10, limit=5, sort="-created_at"
        )


class TestCompareOffers:

    async def test_passes_in_filter_with_user_scope(self):
        repo = _make_repo()
        await repo.compare_offers(USER_ID, [OFFER_ID, OFFER_ID_2])
        call_args = repo.find_many.call_args
        filters = call_args.args[0]
        assert filters["user_id"] == USER_ID
        assert set(filters["_id"]["$in"]) == {OFFER_ID, OFFER_ID_2}
