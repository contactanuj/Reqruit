"""Repository for CareerVitals documents."""

from beanie import PydanticObjectId

from src.db.documents.career_vitals import CareerVitals
from src.repositories.base import BaseRepository


class CareerVitalsRepository(BaseRepository[CareerVitals]):
    """Data access layer for career vitals assessments."""

    def __init__(self) -> None:
        super().__init__(CareerVitals)

    async def get_latest(self, user_id: PydanticObjectId) -> CareerVitals | None:
        """Get the most recent career vitals assessment for a user."""
        results = await self.find_many(
            filters={"user_id": user_id},
            sort="-created_at",
            limit=1,
        )
        return results[0] if results else None

    async def get_history(
        self, user_id: PydanticObjectId, limit: int = 10
    ) -> list[CareerVitals]:
        """Get assessment history for trend analysis."""
        return await self.find_many(
            filters={"user_id": user_id},
            sort="-created_at",
            limit=limit,
        )
