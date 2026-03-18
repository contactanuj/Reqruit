"""
LLM usage repository — data access for LLM usage tracking records.

Provides query methods for rate limiting and cost tracking.
"""

from datetime import datetime

from beanie import PydanticObjectId

from src.db.documents.llm_usage import LLMUsage
from src.repositories.base import BaseRepository


class LLMUsageRepository(BaseRepository[LLMUsage]):
    """LLMUsage-specific data access methods."""

    def __init__(self) -> None:
        super().__init__(LLMUsage)

    async def count_recent_for_user(
        self, user_id: PydanticObjectId, since: datetime
    ) -> int:
        """Count LLM usage records for a user since the given timestamp."""
        return await self.count(
            {"user_id": user_id, "created_at": {"$gte": since}}
        )
