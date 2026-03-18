"""Repository for UserActivity documents — daily action tracking."""

from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId

from src.db.documents.user_activity import UserActivity
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class UserActivityRepository(BaseRepository[UserActivity]):
    """Data access for daily user activity records."""

    def __init__(self) -> None:
        super().__init__(UserActivity)

    async def get_today(self, user_id: PydanticObjectId) -> UserActivity | None:
        """Get today's activity record for a user."""
        today = _today_midnight()
        return await self.find_one({"user_id": user_id, "date": today})

    async def get_or_create_today(self, user_id: PydanticObjectId) -> UserActivity:
        """Get or create today's activity record for a user."""
        existing = await self.get_today(user_id)
        if existing:
            return existing
        doc = UserActivity(user_id=user_id, date=_today_midnight())
        return await self.create(doc)

    async def get_streak(self, user_id: PydanticObjectId) -> int:
        """Return the current streak_count from the latest activity record."""
        records = await self.find_many(
            filters={"user_id": user_id},
            sort="-date",
            limit=1,
        )
        if not records:
            return 0
        return records[0].streak_count

    async def get_history(
        self,
        user_id: PydanticObjectId,
        from_date: datetime,
        to_date: datetime,
    ) -> list[UserActivity]:
        """Get activity records for a date range, sorted by date descending."""
        return await self.find_many(
            filters={
                "user_id": user_id,
                "date": {"$gte": from_date, "$lte": to_date},
            },
            sort="-date",
            limit=90,
        )


def _today_midnight() -> datetime:
    """Return today's date at midnight UTC."""
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
