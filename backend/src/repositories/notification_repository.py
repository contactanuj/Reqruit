"""
Repositories for notification subscriptions and preferences.

NotificationSubscriptionRepository handles Web Push subscription CRUD with
user-level uniqueness. NotificationPreferencesRepository handles per-user
preference upserts (create-or-update semantics).
"""

from typing import Any

import structlog
from beanie import PydanticObjectId

from src.db.documents.notification_preferences import NotificationPreferences
from src.db.documents.notification_subscription import NotificationSubscription
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class NotificationSubscriptionRepository(BaseRepository[NotificationSubscription]):
    """CRUD operations for Web Push subscriptions."""

    def __init__(self) -> None:
        super().__init__(NotificationSubscription)

    async def get_by_user(self, user_id: PydanticObjectId) -> NotificationSubscription | None:
        """Find the push subscription for a given user."""
        return await self.find_one({"user_id": user_id})

    async def delete_by_user(self, user_id: PydanticObjectId) -> int:
        """Remove all subscriptions for a user. Returns count of deleted documents."""
        return await self.delete_many({"user_id": user_id})


class NotificationPreferencesRepository(BaseRepository[NotificationPreferences]):
    """CRUD operations for per-user notification preferences."""

    def __init__(self) -> None:
        super().__init__(NotificationPreferences)

    async def get_by_user(self, user_id: PydanticObjectId) -> NotificationPreferences | None:
        """Find the notification preferences for a given user."""
        return await self.find_one({"user_id": user_id})

    async def upsert_by_user(
        self,
        user_id: PydanticObjectId,
        prefs_dict: dict[str, Any],
    ) -> NotificationPreferences:
        """
        Create or update notification preferences for a user.

        If preferences exist, merges the provided fields. If not, creates a
        new document with defaults for any unspecified fields.

        Args:
            user_id: The user to upsert preferences for.
            prefs_dict: Dict of preference fields to set.

        Returns:
            The created or updated NotificationPreferences document.
        """
        existing = await self.get_by_user(user_id)
        if existing is not None:
            await existing.set(prefs_dict)
            return existing
        doc = NotificationPreferences(user_id=user_id, **prefs_dict)
        return await self.create(doc)
