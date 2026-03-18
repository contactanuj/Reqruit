"""
Notification preferences document — per-user opt-in/opt-out for notification categories.

Each user has one preferences document. Missing documents fall back to defaults
(all categories enabled except market_alert). The unique index on user_id
ensures one preferences record per user.
"""

from beanie import Indexed, PydanticObjectId

from src.db.base_document import TimestampedDocument


class NotificationPreferences(TimestampedDocument):
    """
    Per-user notification preference flags.

    Fields:
        user_id: The user these preferences belong to (unique).
        daily_shortlist: Opt-in for daily job shortlist notifications.
        interview_reminder: Opt-in for interview reminder notifications.
        application_update: Opt-in for application status update notifications.
        offer_received: Opt-in for offer received notifications.
        nudge: Opt-in for smart nudge notifications.
        market_alert: Opt-in for market signal alerts (default off).
    """

    user_id: Indexed(PydanticObjectId, unique=True)
    daily_shortlist: bool = True
    interview_reminder: bool = True
    application_update: bool = True
    offer_received: bool = True
    nudge: bool = True
    market_alert: bool = False

    class Settings:
        name = "notification_preferences"
