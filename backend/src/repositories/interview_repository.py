"""
Interview repository — owner-scoped CRUD for interview records.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.interview import Interview
from src.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[Interview]):
    """Interview-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Interview)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, interview_id: PydanticObjectId
    ) -> Interview | None:
        """Fetch a specific interview, verifying ownership by user_id."""
        return await self.find_one({"_id": interview_id, "user_id": user_id})

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Interview]:
        """List interviews for a user, optionally filtered by application_id."""
        filters: dict = {"user_id": user_id}
        if application_id:
            filters["application_id"] = application_id
        return await self.find_many(
            filters, skip=skip, limit=limit, sort="scheduled_at"
        )

    async def get_for_application(
        self, user_id: PydanticObjectId, application_id: PydanticObjectId
    ) -> list[Interview]:
        """All interviews for a specific application, owner-scoped."""
        return await self.find_many(
            {"user_id": user_id, "application_id": application_id},
            sort="scheduled_at",
        )
