"""Tests for MarketConfigRepository."""

from unittest.mock import AsyncMock, patch

from src.db.documents.market_config import MarketConfig
from src.repositories.market_config_repository import MarketConfigRepository


class TestMarketConfigRepository:
    """Tests for MarketConfigRepository domain methods."""

    def test_init(self) -> None:
        repo = MarketConfigRepository()
        assert repo._model is MarketConfig

    async def test_get_by_region_found(self) -> None:
        repo = MarketConfigRepository()
        mock_config = MarketConfig(region_code="IN", region_name="India")
        repo.find_one = AsyncMock(return_value=mock_config)

        result = await repo.get_by_region("IN")

        assert result is mock_config
        repo.find_one.assert_called_once_with({"region_code": "IN"})

    async def test_get_by_region_not_found(self) -> None:
        repo = MarketConfigRepository()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_region("ZZ")

        assert result is None
        repo.find_one.assert_called_once_with({"region_code": "ZZ"})

    async def test_get_by_region_passes_code_through(self) -> None:
        """Region code is passed as-is (caller is responsible for uppercasing)."""
        repo = MarketConfigRepository()
        repo.find_one = AsyncMock(return_value=None)

        await repo.get_by_region("in")

        repo.find_one.assert_called_once_with({"region_code": "in"})

    async def test_inherits_base_repository_methods(self) -> None:
        """MarketConfigRepository should inherit CRUD from BaseRepository."""
        repo = MarketConfigRepository()
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "find_many")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "count")
