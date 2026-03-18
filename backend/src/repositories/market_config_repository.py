"""
Repository for MarketConfig documents.

Provides region-code-based lookup on top of the generic BaseRepository CRUD.
"""

from src.db.documents.market_config import MarketConfig
from src.repositories.base import BaseRepository


class MarketConfigRepository(BaseRepository[MarketConfig]):
    """Market configuration data access."""

    def __init__(self) -> None:
        super().__init__(MarketConfig)

    async def get_by_region(self, region_code: str) -> MarketConfig | None:
        """Find a market config by its ISO 3166-1 alpha-2 region code."""
        return await self.find_one({"region_code": region_code})
