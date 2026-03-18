"""
Repository for Nudge documents with idempotent creation.

The create_if_not_exists method uses the unique (user_id, application_id, nudge_type)
index to prevent duplicate nudges for the same application and type.
"""

from datetime import UTC, datetime

import structlog
from beanie import PydanticObjectId

from src.db.documents.nudge import Nudge, NudgeStatus
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class NudgeRepository(BaseRepository[Nudge]):
    """CRUD operations for Nudge with idempotent creation."""

    def __init__(self) -> None:
        super().__init__(Nudge)

    async def create_if_not_exists(self, nudge: Nudge) -> Nudge | None:
        """
        Insert a nudge if no duplicate (user_id, application_id, nudge_type) exists.

        Returns the nudge if created, None if it already exists.
        """
        existing = await self.find_one({
            "user_id": nudge.user_id,
            "application_id": nudge.application_id,
            "nudge_type": nudge.nudge_type,
        })
        if existing is not None:
            return None
        return await self.create(nudge)

    async def get_pending_by_user(
        self,
        user_id: PydanticObjectId,
        limit: int = 20,
    ) -> list[Nudge]:
        """Return pending nudges for a user, sorted by trigger_date desc."""
        return await self.find_many(
            filters={"user_id": user_id, "status": NudgeStatus.PENDING},
            limit=limit,
            sort="-trigger_date",
        )

    async def get_by_user_and_application(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId,
    ) -> list[Nudge]:
        """Return all nudges for a specific application."""
        return await self.find_many(
            filters={"user_id": user_id, "application_id": application_id},
            sort="-created_at",
        )

    async def mark_seen(self, nudge_id: PydanticObjectId) -> Nudge | None:
        """Set status to SEEN and record seen_at timestamp."""
        return await self.update(nudge_id, {
            "status": NudgeStatus.SEEN,
            "seen_at": datetime.now(UTC),
        })

    async def mark_dismissed(self, nudge_id: PydanticObjectId) -> Nudge | None:
        """Set status to DISMISSED and record dismissed_at timestamp."""
        return await self.update(nudge_id, {
            "status": NudgeStatus.DISMISSED,
            "dismissed_at": datetime.now(UTC),
        })

    async def mark_acted_on(self, nudge_id: PydanticObjectId) -> Nudge | None:
        """Set status to ACTED_ON."""
        return await self.update(nudge_id, {"status": NudgeStatus.ACTED_ON})

    async def count_pending_by_user(self, user_id: PydanticObjectId) -> int:
        """Return count of pending nudges for badge display."""
        return await self.count({"user_id": user_id, "status": NudgeStatus.PENDING})

    async def delete_by_application(self, application_id: PydanticObjectId) -> int:
        """Remove all nudges for an application (cleanup on archive/delete)."""
        return await self.delete_many({"application_id": application_id})
