"""Repository for OnboardingPlan documents."""

from beanie import PydanticObjectId

from src.db.documents.onboarding_plan import OnboardingPlan
from src.repositories.base import BaseRepository


class OnboardingPlanRepository(BaseRepository[OnboardingPlan]):
    """Data access layer for onboarding plans."""

    async def get_active(self, user_id: PydanticObjectId) -> OnboardingPlan | None:
        """Get the most recent onboarding plan for a user."""
        results = await self.find_many(
            filters={"user_id": user_id},
            sort="-created_at",
            limit=1,
        )
        return results[0] if results else None

    async def get_by_id_and_user(
        self, plan_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> OnboardingPlan | None:
        """Fetch a plan by ID scoped to a user."""
        return await self.find_one({"_id": plan_id, "user_id": user_id})
