"""
Push notification service — manages notification subscriptions and delivery.

Handles:
- Registering push notification subscriptions (Web Push API)
- Sending notifications for key events (new shortlist, interview reminder, etc.)
- Managing notification preferences per user

All state is persisted in MongoDB via the notification subscription and
preferences repositories, following the project's repository pattern.
"""

import structlog
from beanie import PydanticObjectId

from src.db.documents.notification_subscription import NotificationSubscription
from src.repositories.notification_repository import (
    NotificationPreferencesRepository,
    NotificationSubscriptionRepository,
)

logger = structlog.get_logger()


class NotificationPayload:
    """Structured notification payload."""

    def __init__(
        self,
        title: str,
        body: str,
        category: str = "general",
        action_url: str = "",
        icon: str = "/static/icons/icon-192.png",
    ) -> None:
        self.title = title
        self.body = body
        self.category = category
        self.action_url = action_url
        self.icon = icon

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "category": self.category,
            "action_url": self.action_url,
            "icon": self.icon,
        }


# Default notification preferences
DEFAULT_PREFERENCES = {
    "daily_shortlist": True,
    "interview_reminder": True,
    "application_update": True,
    "offer_received": True,
    "nudge": True,
    "market_alert": False,
}


class PushNotificationService:
    """Manages push notification subscriptions and delivery."""

    def __init__(
        self,
        subscription_repo: NotificationSubscriptionRepository,
        preferences_repo: NotificationPreferencesRepository,
    ) -> None:
        self._subscription_repo = subscription_repo
        self._preferences_repo = preferences_repo

    async def register_subscription(
        self, user_id: PydanticObjectId, subscription: dict
    ) -> dict:
        """
        Register a Web Push subscription for a user.

        If a subscription already exists for this user, it is replaced.

        Args:
            user_id: User identifier.
            subscription: Web Push API subscription object
                         (endpoint, keys.p256dh, keys.auth).

        Returns:
            Registration confirmation dict.
        """
        existing = await self._subscription_repo.get_by_user(user_id)
        if existing is not None:
            await existing.set({
                "endpoint": subscription.get("endpoint", ""),
                "keys": subscription.get("keys", {}),
            })
        else:
            doc = NotificationSubscription(
                user_id=user_id,
                endpoint=subscription.get("endpoint", ""),
                keys=subscription.get("keys", {}),
            )
            await self._subscription_repo.create(doc)

        logger.info("push_subscription_registered", user_id=str(user_id))
        return {
            "status": "registered",
            "user_id": str(user_id),
        }

    async def unregister_subscription(self, user_id: PydanticObjectId) -> dict:
        """Remove a user's push subscription."""
        await self._subscription_repo.delete_by_user(user_id)
        logger.info("push_subscription_removed", user_id=str(user_id))
        return {"status": "unregistered", "user_id": str(user_id)}

    async def get_preferences(self, user_id: PydanticObjectId) -> dict:
        """Get notification preferences for a user."""
        doc = await self._preferences_repo.get_by_user(user_id)
        if doc is None:
            return dict(DEFAULT_PREFERENCES)
        return {
            "daily_shortlist": doc.daily_shortlist,
            "interview_reminder": doc.interview_reminder,
            "application_update": doc.application_update,
            "offer_received": doc.offer_received,
            "nudge": doc.nudge,
            "market_alert": doc.market_alert,
        }

    async def update_preferences(
        self, user_id: PydanticObjectId, preferences: dict
    ) -> dict:
        """Update notification preferences for a user."""
        # Filter to only known preference fields
        valid_keys = set(DEFAULT_PREFERENCES.keys())
        filtered = {k: v for k, v in preferences.items() if k in valid_keys}

        doc = await self._preferences_repo.upsert_by_user(user_id, filtered)
        return {
            "daily_shortlist": doc.daily_shortlist,
            "interview_reminder": doc.interview_reminder,
            "application_update": doc.application_update,
            "offer_received": doc.offer_received,
            "nudge": doc.nudge,
            "market_alert": doc.market_alert,
        }

    async def send_notification(
        self, user_id: PydanticObjectId, payload: NotificationPayload
    ) -> dict:
        """
        Send a push notification to a user.

        Checks subscription existence and preference opt-in before sending.
        In production, this would call the Web Push protocol endpoint.

        Returns:
            Delivery status dict.
        """
        sub = await self._subscription_repo.get_by_user(user_id)
        if sub is None:
            return {"status": "skipped", "reason": "no_subscription"}

        prefs = await self.get_preferences(user_id)
        if not prefs.get(payload.category, True):
            return {"status": "skipped", "reason": "opted_out"}

        # In production: call Web Push API with subscription endpoint
        logger.info(
            "push_notification_sent",
            user_id=str(user_id),
            title=payload.title,
            category=payload.category,
        )
        return {
            "status": "sent",
            "user_id": str(user_id),
            "payload": payload.to_dict(),
        }

    async def send_bulk(
        self, user_ids: list[PydanticObjectId], payload: NotificationPayload
    ) -> dict:
        """Send a notification to multiple users."""
        results = []
        for uid in user_ids:
            result = await self.send_notification(uid, payload)
            results.append({"user_id": str(uid), **result})
        sent = sum(1 for r in results if r["status"] == "sent")
        return {"total": len(user_ids), "sent": sent, "results": results}
