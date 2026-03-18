"""
Repository for JobShortlist documents — daily curated job recommendations.

Provides methods for creating, retrieving, and managing daily shortlists
with user-scoped queries and date-based lookups.
"""

from datetime import datetime

from beanie import PydanticObjectId

from src.db.documents.job_shortlist import JobShortlist
from src.repositories.base import BaseRepository


class JobShortlistRepository(BaseRepository[JobShortlist]):
    """CRUD operations for JobShortlist with date-based queries."""

    def __init__(self) -> None:
        super().__init__(JobShortlist)

    async def get_by_user_and_date(
        self,
        user_id: PydanticObjectId,
        date: datetime,
    ) -> JobShortlist | None:
        """Return the shortlist for a user on a specific date."""
        return await self.find_one({"user_id": user_id, "date": date})

    async def get_latest_by_user(
        self,
        user_id: PydanticObjectId,
    ) -> JobShortlist | None:
        """Return the most recent shortlist for a user."""
        results = await self.find_many(
            filters={"user_id": user_id},
            limit=1,
            sort="-date",
        )
        return results[0] if results else None

    async def get_history(
        self,
        user_id: PydanticObjectId,
        limit: int = 7,
    ) -> list[JobShortlist]:
        """Return recent shortlists for a user, sorted by date descending."""
        return await self.find_many(
            filters={"user_id": user_id},
            limit=limit,
            sort="-date",
        )
