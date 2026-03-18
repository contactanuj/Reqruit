"""
Repository for NegotiationSession CRUD with user-scoped queries.
"""

from beanie import PydanticObjectId

from src.db.documents.negotiation_session import NegotiationSession
from src.repositories.base import BaseRepository


class NegotiationSessionRepository(BaseRepository[NegotiationSession]):
    """Data access for negotiation session documents."""

    def __init__(self) -> None:
        super().__init__(NegotiationSession)

    async def get_user_sessions(
        self,
        user_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 20,
    ) -> list[NegotiationSession]:
        """List sessions for a user, sorted newest first."""
        return await self.find_many(
            {"user_id": user_id},
            sort="-created_at",
            skip=skip,
            limit=limit,
        )

    async def get_by_user_and_id(
        self,
        user_id: PydanticObjectId,
        session_id: PydanticObjectId,
    ) -> NegotiationSession | None:
        """Get a session owned by the user, or None."""
        return await self.find_one(
            {"_id": session_id, "user_id": user_id}
        )

    async def delete_by_user_and_id(
        self,
        user_id: PydanticObjectId,
        session_id: PydanticObjectId,
    ) -> bool:
        """Delete a session owned by the user. Returns True if deleted."""
        session = await self.get_by_user_and_id(user_id, session_id)
        if session is None:
            return False
        await session.delete()
        return True
