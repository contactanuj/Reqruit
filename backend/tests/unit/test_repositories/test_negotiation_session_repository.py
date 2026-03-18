"""
Tests for NegotiationSessionRepository.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.repositories.negotiation_session_repository import NegotiationSessionRepository


def _make_repo() -> NegotiationSessionRepository:
    repo = NegotiationSessionRepository.__new__(NegotiationSessionRepository)
    return repo


def _uid() -> PydanticObjectId:
    return PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _sid() -> PydanticObjectId:
    return PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


async def test_get_user_sessions_delegates():
    repo = _make_repo()
    sessions = [MagicMock(), MagicMock()]
    repo.find_many = AsyncMock(return_value=sessions)

    result = await repo.get_user_sessions(_uid(), skip=0, limit=20)

    assert result == sessions
    repo.find_many.assert_called_once_with(
        {"user_id": _uid()},
        sort="-created_at",
        skip=0,
        limit=20,
    )


async def test_get_user_sessions_with_pagination():
    repo = _make_repo()
    repo.find_many = AsyncMock(return_value=[])

    result = await repo.get_user_sessions(_uid(), skip=20, limit=10)

    assert result == []
    repo.find_many.assert_called_once_with(
        {"user_id": _uid()},
        sort="-created_at",
        skip=20,
        limit=10,
    )


async def test_get_by_user_and_id_found():
    repo = _make_repo()
    session = MagicMock()
    repo.find_one = AsyncMock(return_value=session)

    result = await repo.get_by_user_and_id(_uid(), _sid())

    assert result is session
    repo.find_one.assert_called_once_with(
        {"_id": _sid(), "user_id": _uid()}
    )


async def test_get_by_user_and_id_not_found():
    repo = _make_repo()
    repo.find_one = AsyncMock(return_value=None)

    result = await repo.get_by_user_and_id(_uid(), _sid())

    assert result is None


async def test_delete_by_user_and_id_success():
    repo = _make_repo()
    session = MagicMock()
    session.delete = AsyncMock()
    repo.find_one = AsyncMock(return_value=session)

    result = await repo.delete_by_user_and_id(_uid(), _sid())

    assert result is True
    session.delete.assert_called_once()


async def test_delete_by_user_and_id_not_found():
    repo = _make_repo()
    repo.find_one = AsyncMock(return_value=None)

    result = await repo.delete_by_user_and_id(_uid(), _sid())

    assert result is False
