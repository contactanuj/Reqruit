"""
Notification subscription document — stores Web Push API subscriptions per user.

Each user can have one active push subscription at a time. The unique index on
user_id ensures no duplicate subscriptions. When a user re-subscribes, the
existing subscription is replaced via upsert.
"""

from beanie import Indexed, PydanticObjectId

from src.db.base_document import TimestampedDocument


class NotificationSubscription(TimestampedDocument):
    """
    A Web Push API subscription for delivering browser push notifications.

    Fields:
        user_id: The user this subscription belongs to (unique).
        endpoint: The push service endpoint URL from the browser.
        keys: The encryption keys (p256dh, auth) for payload encryption.
    """

    user_id: Indexed(PydanticObjectId, unique=True)
    endpoint: str
    keys: dict

    class Settings:
        name = "notification_subscriptions"
