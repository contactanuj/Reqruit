"""
Repository for CalendarSignal documents with idempotent creation.

The create_if_not_exists method uses the unique (user_id, event_id) index
to atomically prevent duplicate signals from the same calendar event.
"""

from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId

from src.db.documents.calendar_signal import CalendarSignal
from src.db.documents.integration_connection import IntegrationProvider
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class CalendarSignalRepository(BaseRepository[CalendarSignal]):
    """CRUD operations for CalendarSignal with idempotent upsert."""

    def __init__(self) -> None:
        super().__init__(CalendarSignal)

    async def create_if_not_exists(self, signal: CalendarSignal) -> CalendarSignal | None:
        """
        Insert a signal if no duplicate (user_id, event_id) exists.

        Returns the signal if created, None if it already exists.
        """
        existing = await self.find_one(
            {"user_id": signal.user_id, "event_id": signal.event_id}
        )
        if existing is not None:
            logger.debug(
                "calendar_signal_duplicate_skipped",
                user_id=str(signal.user_id),
                event_id=signal.event_id,
            )
            return None
        return await self.create(signal)

    async def get_upcoming_interviews(
        self,
        user_id: PydanticObjectId,
        days_ahead: int = 7,
    ) -> list[CalendarSignal]:
        """Return upcoming interview events within days_ahead, sorted by event_date."""
        now = datetime.now(UTC)
        cutoff = now + timedelta(days=days_ahead)
        return await self.find_many(
            filters={
                "user_id": user_id,
                "event_date": {"$gte": now, "$lte": cutoff},
            },
            sort="event_date",
        )

    async def get_nudge_eligible(
        self, user_id: PydanticObjectId
    ) -> list[CalendarSignal]:
        """Return signals eligible for preparation nudges (3-7 days out)."""
        now = datetime.now(UTC)
        min_date = now + timedelta(days=3)
        max_date = now + timedelta(days=7)
        return await self.find_many(
            filters={
                "user_id": user_id,
                "nudge_eligible": True,
                "event_date": {"$gte": min_date, "$lte": max_date},
            },
            sort="event_date",
        )

    async def delete_by_user_and_provider(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
    ) -> int:
        """Bulk delete all calendar signals for a user+provider. Returns delete count."""
        return await self.delete_many(
            {"user_id": user_id, "provider": provider.value}
        )

    async def update_nudge_eligible(
        self,
        signal_id: PydanticObjectId,
        eligible: bool,
    ) -> CalendarSignal | None:
        """Mark a signal's nudge eligibility (e.g. after nudge is sent)."""
        return await self.update(signal_id, {"nudge_eligible": eligible})
