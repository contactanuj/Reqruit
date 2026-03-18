"""
Job discovery service — preference management and AI-powered job matching.

Handles storing user discovery preferences on their profile and generating
fit scores for jobs against those preferences. The actual shortlist generation
is handled by the Celery task in discovery_tasks.
"""

import structlog
from beanie import PydanticObjectId

from src.db.documents.job_shortlist import DiscoveryPreferences, JobShortlist
from src.repositories.job_shortlist_repository import JobShortlistRepository
from src.repositories.profile_repository import ProfileRepository

logger = structlog.get_logger()


class JobDiscoveryService:
    """Manages discovery preferences and shortlist retrieval."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        shortlist_repo: JobShortlistRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._shortlist_repo = shortlist_repo

    async def update_preferences(
        self,
        user_id: PydanticObjectId,
        preferences: DiscoveryPreferences,
    ) -> DiscoveryPreferences:
        """
        Save discovery preferences on the user's profile.

        Returns the saved preferences.
        """
        profile = await self._profile_repo.find_one({"user_id": user_id})
        if profile is None:
            logger.warning("discovery_preferences_no_profile", user_id=str(user_id))
            raise ValueError("Profile not found")

        await self._profile_repo.update(
            profile.id,
            {"discovery_preferences": preferences.model_dump()},
        )
        logger.info("discovery_preferences_updated", user_id=str(user_id))
        return preferences

    async def get_preferences(
        self,
        user_id: PydanticObjectId,
    ) -> DiscoveryPreferences | None:
        """Return the user's current discovery preferences, or None."""
        profile = await self._profile_repo.find_one({"user_id": user_id})
        if profile is None:
            return None
        raw = getattr(profile, "discovery_preferences", None)
        if raw is None:
            return None
        if isinstance(raw, dict):
            return DiscoveryPreferences(**raw)
        return raw

    async def get_latest_shortlist(
        self,
        user_id: PydanticObjectId,
    ) -> JobShortlist | None:
        """Return the most recent shortlist for a user."""
        return await self._shortlist_repo.get_latest_by_user(user_id)

    async def get_shortlist_history(
        self,
        user_id: PydanticObjectId,
        limit: int = 7,
    ) -> list[JobShortlist]:
        """Return recent shortlists for a user."""
        return await self._shortlist_repo.get_history(user_id, limit=limit)
