"""
Repository for EmailSignal documents with idempotent creation.

The create_if_not_exists method uses the unique (user_id, message_id) index
to atomically prevent duplicate signals from the same email message.
"""

import structlog
from beanie import PydanticObjectId

from src.db.documents.email_signal import EmailSignal
from src.db.documents.integration_connection import IntegrationProvider
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class EmailSignalRepository(BaseRepository[EmailSignal]):
    """CRUD operations for EmailSignal with idempotent upsert."""

    def __init__(self) -> None:
        super().__init__(EmailSignal)

    async def create_if_not_exists(self, signal: EmailSignal) -> EmailSignal | None:
        """
        Insert a signal if no duplicate (user_id, message_id) exists.

        Returns the signal if created, None if it already exists.
        """
        existing = await self.find_one(
            {"user_id": signal.user_id, "message_id": signal.message_id}
        )
        if existing is not None:
            logger.debug(
                "email_signal_duplicate_skipped",
                user_id=str(signal.user_id),
                message_id=signal.message_id,
            )
            return None
        return await self.create(signal)

    async def get_by_user(
        self,
        user_id: PydanticObjectId,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailSignal]:
        """Return signals for a user, sorted by created_at descending."""
        return await self.find_many(
            filters={"user_id": user_id},
            skip=offset,
            limit=limit,
            sort="-created_at",
        )

    async def get_by_user_and_pattern(
        self,
        user_id: PydanticObjectId,
        pattern: str,
    ) -> list[EmailSignal]:
        """Return signals for a user filtered by matched_pattern."""
        return await self.find_many(
            filters={"user_id": user_id, "matched_pattern": pattern},
            sort="-created_at",
        )

    async def delete_by_user_and_provider(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
    ) -> int:
        """Bulk delete all signals for a user+provider. Returns delete count."""
        return await self.delete_many(
            {"user_id": user_id, "provider": provider.value}
        )

    async def update_source_to_user_reported(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
    ) -> int:
        """Re-attribute signals as user-reported on non-purge disconnect."""
        result = await EmailSignal.find(
            {"user_id": user_id, "provider": provider.value}
        ).update_many({"$set": {"source": "user-reported"}})
        return result.modified_count if result else 0
