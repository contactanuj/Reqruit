"""
STAR story repository — owner-scoped CRUD for behavioral interview stories.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.star_story import STARStory
from src.repositories.base import BaseRepository


class STARStoryRepository(BaseRepository[STARStory]):
    """STAR story data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(STARStory)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, story_id: PydanticObjectId
    ) -> STARStory | None:
        """Fetch a specific STAR story, verifying ownership by user_id."""
        return await self.find_one({"_id": story_id, "user_id": user_id})

    async def get_all_for_user(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 100
    ) -> list[STARStory]:
        """List all STAR stories for a user, sorted newest first."""
        return await self.find_many(
            {"user_id": user_id}, skip=skip, limit=limit, sort="-created_at"
        )

    async def get_by_tags(
        self, user_id: PydanticObjectId, tags: list[str]
    ) -> list[STARStory]:
        """Find stories matching any of the given tags."""
        return await self.find_many(
            {"user_id": user_id, "tags": {"$in": tags}}, sort="-created_at"
        )
