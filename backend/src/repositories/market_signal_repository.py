"""Repository for MarketSignal documents."""

from beanie import PydanticObjectId

from src.db.documents.market_signal import MarketSignal
from src.repositories.base import BaseRepository


class MarketSignalRepository(BaseRepository[MarketSignal]):
    """Data access layer for market signals."""

    def __init__(self) -> None:
        super().__init__(MarketSignal)

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        signal_type: str | None = None,
        limit: int = 20,
    ) -> list[MarketSignal]:
        """Get signals relevant to a user (user-specific + global)."""
        filters: dict = {
            "$or": [{"user_id": user_id}, {"user_id": None}],
        }
        if signal_type:
            filters["signal_type"] = signal_type
        return await self.find_many(filters=filters, sort="-created_at", limit=limit)

    async def get_by_industry(
        self, industry: str, limit: int = 20
    ) -> list[MarketSignal]:
        """Get signals for a specific industry."""
        return await self.find_many(
            filters={"industry": industry},
            sort="-created_at",
            limit=limit,
        )
