"""
Unit tests for LLMUsageRepository.

Tests the rate-limiting query method count_recent_for_user().
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.repositories.llm_usage_repository import LLMUsageRepository


async def test_count_recent_for_user_delegates_to_count():
    """count_recent_for_user calls self.count with correct user_id and $gte filter."""
    repo = LLMUsageRepository.__new__(LLMUsageRepository)
    repo._model = MagicMock()
    repo.count = AsyncMock(return_value=7)

    user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    since = datetime(2026, 3, 13, 10, 0, 0)

    result = await repo.count_recent_for_user(user_id, since)

    assert result == 7
    repo.count.assert_called_once_with(
        {"user_id": user_id, "created_at": {"$gte": since}}
    )


async def test_count_recent_for_user_returns_zero_when_no_records():
    """count_recent_for_user returns 0 when count returns 0."""
    repo = LLMUsageRepository.__new__(LLMUsageRepository)
    repo._model = MagicMock()
    repo.count = AsyncMock(return_value=0)

    user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    since = datetime(2026, 3, 13, 10, 0, 0)

    result = await repo.count_recent_for_user(user_id, since)

    assert result == 0
