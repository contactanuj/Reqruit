"""
Profile repository — data access methods for user career profiles.

A profile is a one-to-one extension of User that holds career data.
The get_or_create pattern simplifies the client — it never needs to
check if a profile exists before reading it.
"""

from beanie import PydanticObjectId

from src.db.documents.profile import Profile
from src.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    """Profile-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Profile)

    async def get_by_user_id(self, user_id: PydanticObjectId) -> Profile | None:
        """Find a profile by the owning user's ObjectId."""
        return await self.find_one({"user_id": user_id})

    async def get_or_create(self, user_id: PydanticObjectId) -> Profile:
        """Get existing profile or create an empty one."""
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            profile = await self.create(Profile(user_id=user_id))
        return profile
