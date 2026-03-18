"""
Mock session repository — owner-scoped CRUD for mock interview sessions.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.mock_session import MockInterviewSession
from src.repositories.base import BaseRepository


class MockSessionRepository(BaseRepository[MockInterviewSession]):
    """Mock session data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(MockInterviewSession)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, session_id: PydanticObjectId
    ) -> MockInterviewSession | None:
        """Fetch a specific mock session, verifying ownership by user_id."""
        return await self.find_one({"_id": session_id, "user_id": user_id})

    async def get_for_interview(
        self,
        user_id: PydanticObjectId,
        interview_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MockInterviewSession]:
        """List mock sessions for a specific interview, owner-scoped."""
        return await self.find_many(
            {"user_id": user_id, "interview_id": interview_id},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )
