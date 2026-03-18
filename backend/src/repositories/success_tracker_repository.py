"""
Repository for ApplicationSuccessTracker documents.

Provides typed query methods and atomic status updates for concurrent safety.
"""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pymongo import ReturnDocument

from src.db.documents.application_success_tracker import ApplicationSuccessTracker
from src.db.documents.enums import OutcomeStatus
from src.repositories.base import BaseRepository


class ApplicationSuccessTrackerRepository(BaseRepository[ApplicationSuccessTracker]):
    """Repository for application outcome tracking with atomic update support."""

    def __init__(self) -> None:
        super().__init__(ApplicationSuccessTracker)

    async def get_by_application(
        self, user_id: PydanticObjectId, application_id: PydanticObjectId
    ) -> ApplicationSuccessTracker | None:
        """Find a tracker by application_id scoped to user_id."""
        return await self.find_one(
            {"user_id": user_id, "application_id": application_id}
        )

    async def atomic_status_update(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId,
        expected_status: OutcomeStatus,
        new_status: OutcomeStatus,
        transition: dict,
    ) -> ApplicationSuccessTracker | None:
        """Atomically update status only if current status matches expected.

        Uses findOneAndUpdate with status precondition for concurrent safety.
        Returns the updated document, or None if precondition failed.
        """
        now = datetime.utcnow()
        result = await ApplicationSuccessTracker.find_one_and_update(
            {
                "user_id": user_id,
                "application_id": application_id,
                "outcome_status": expected_status,
            },
            {
                "$set": {
                    "outcome_status": new_status,
                    "last_updated": now,
                    "updated_at": now,
                },
                "$push": {"outcome_transitions": transition},
            },
            response_type=ReturnDocument.AFTER,
        )
        return result

    async def aggregate_summary(self, user_id: PydanticObjectId) -> dict:
        """Run a MongoDB aggregation pipeline for analytics summary.

        Uses $facet for single-pass computation of status counts and breakdowns.
        """
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$facet": {
                "status_counts": [
                    {"$group": {"_id": "$outcome_status", "count": {"$sum": 1}}},
                ],
                "by_submission_method": [
                    {"$group": {"_id": "$submission_method", "count": {"$sum": 1}}},
                ],
                "by_resume_strategy": [
                    {"$group": {"_id": "$resume_strategy", "count": {"$sum": 1}}},
                ],
                "by_day_of_week": [
                    {"$match": {"submitted_at": {"$ne": None}}},
                    {"$group": {"_id": {"$dayOfWeek": "$submitted_at"}, "count": {"$sum": 1}}},
                ],
                "by_hour": [
                    {"$match": {"submitted_at": {"$ne": None}}},
                    {"$group": {"_id": {"$hour": "$submitted_at"}, "count": {"$sum": 1}}},
                ],
                "total": [{"$count": "count"}],
            }},
        ]
        result = await ApplicationSuccessTracker.aggregate(pipeline).to_list()
        return result[0] if result else {}

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ApplicationSuccessTracker]:
        """Paginated query for a user's trackers with optional filters."""
        query_filters: dict[str, Any] = {"user_id": user_id}
        if filters:
            query_filters.update(filters)
        return await self.find_many(query_filters, skip=skip, limit=limit, sort="-last_updated")
