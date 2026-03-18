"""
Application repository — data access for the user-job pipeline join table.

Every query here is scoped to a user_id for ownership enforcement.
The kanban query returns all applications without pagination because
a personal job tracker rarely exceeds 500 active applications.
"""

from beanie import PydanticObjectId

from src.db.documents.application import Application
from src.db.documents.enums import ApplicationStatus
from src.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Application-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(Application)

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
        status: ApplicationStatus | None = None,
    ) -> list[Application]:
        """List applications for a user, optionally filtered by status."""
        filters: dict = {"user_id": user_id}
        if status:
            filters["status"] = status
        return await self.find_many(filters, skip=skip, limit=limit, sort="-created_at")

    async def get_by_user_and_id(
        self, user_id: PydanticObjectId, application_id: PydanticObjectId
    ) -> Application | None:
        """Fetch a specific application, verifying ownership by user_id."""
        return await self.find_one({"_id": application_id, "user_id": user_id})

    async def get_kanban(
        self,
        user_id: PydanticObjectId,
        exclude_statuses: list[ApplicationStatus] | None = None,
    ) -> list[Application]:
        """All applications for kanban board (no pagination — personal scale)."""
        filters: dict = {"user_id": user_id}
        if exclude_statuses:
            filters["status"] = {"$nin": [s.value for s in exclude_statuses]}
        return await self.find_many(filters, limit=500, sort="-created_at")

    async def get_for_user_by_statuses(
        self,
        user_id: PydanticObjectId,
        statuses: list[ApplicationStatus],
        skip: int = 0,
        limit: int = 50,
    ) -> list[Application]:
        """List applications for a user filtered to specific statuses."""
        return await self.find_many(
            {"user_id": user_id, "status": {"$in": [s.value for s in statuses]}},
            skip=skip,
            limit=limit,
            sort="-created_at",
        )

    async def get_by_job_and_user(
        self, job_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Application | None:
        """Find the application linking a specific job and user."""
        return await self.find_one({"job_id": job_id, "user_id": user_id})

    async def find_in_progress_assembly(
        self, user_id: PydanticObjectId
    ) -> Application | None:
        """Find an in-progress assembly for a user.

        Matches applications that have an active assembly thread (thread_id set)
        and haven't been finalized (still SAVED — not yet APPLIED/WITHDRAWN).
        Used by the application assembly route to prevent duplicate
        concurrent assemblies for the same user (AC #5).
        """
        return await self.find_one({
            "user_id": user_id,
            "status": ApplicationStatus.SAVED,
            "thread_id": {"$nin": [None, ""]},
        })
