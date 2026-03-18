"""
Repository for SkillsProfile documents.

Provides user-based lookup on top of the generic BaseRepository CRUD.
"""

from beanie import PydanticObjectId

from src.db.documents.skills_profile import SkillsProfile
from src.repositories.base import BaseRepository


class SkillsProfileRepository(BaseRepository[SkillsProfile]):
    """Skills profile data access."""

    def __init__(self) -> None:
        super().__init__(SkillsProfile)

    async def get_by_user(self, user_id: PydanticObjectId) -> SkillsProfile | None:
        """Find a skills profile by user ID."""
        return await self.find_one({"user_id": user_id})
