"""
Outreach message repository — owner-scoped CRUD for outreach messages.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.outreach_message import OutreachMessage
from src.repositories.base import BaseRepository


class OutreachMessageRepository(BaseRepository[OutreachMessage]):
    """Outreach-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(OutreachMessage)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, message_id: PydanticObjectId
    ) -> OutreachMessage | None:
        """Fetch a specific outreach message, verifying ownership."""
        return await self.find_one({"_id": message_id, "user_id": user_id})

    async def get_for_application(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OutreachMessage]:
        """List outreach messages for a specific application, owner-scoped."""
        return await self.find_many(
            {"user_id": user_id, "application_id": application_id},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OutreachMessage]:
        """List all outreach messages for a user."""
        return await self.find_many(
            {"user_id": user_id},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )
