"""
Resume repository — data access methods for uploaded resume documents.

Resumes have a master flag — at most one resume per user is the master.
The unset_master_for_user method ensures this invariant when switching masters.
"""

from beanie import PydanticObjectId

from src.db.documents.resume import Resume
from src.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    """Resume-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Resume)

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, resume_id: PydanticObjectId
    ) -> Resume | None:
        """Get a resume by ID scoped to a specific user (single query with owner check)."""
        return await self.find_one({"_id": resume_id, "user_id": user_id})

    async def get_master_resume(self, user_id: PydanticObjectId) -> Resume | None:
        """Find the master resume for a user. Returns None if none is marked master."""
        return await self.find_one({"user_id": user_id, "is_master": True})

    async def get_all_for_user(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 20
    ) -> list[Resume]:
        """List all resumes for a user, sorted newest first."""
        return await self.find_many(
            {"user_id": user_id}, skip=skip, limit=limit, sort="-created_at"
        )

    async def unset_master_for_user(self, user_id: PydanticObjectId) -> None:
        """Clear is_master=True on all resumes for this user."""
        await Resume.find({"user_id": user_id, "is_master": True}).update(
            {"$set": {"is_master": False}}
        )

    async def count_for_user(self, user_id: PydanticObjectId) -> int:
        """Count total resumes for a user."""
        return await self.count({"user_id": user_id})
