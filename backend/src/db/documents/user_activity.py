"""
UserActivity document — daily action tracking with quality-weighted XP.

Each user gets one UserActivity document per day. Actions are appended
throughout the day, and total_xp is the sum of all action XP values.
"""

from datetime import UTC, datetime

from beanie import Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from src.db.base_document import TimestampedDocument


class ActivityEntry(BaseModel):
    """A single tracked action within a day."""

    action_type: str
    xp_earned: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)


class UserActivity(TimestampedDocument):
    """
    Daily activity record for a user.

    One document per user per day. Actions are appended as ActivityEntry
    items. XP is deterministic — looked up from XP_TABLE, never LLM-generated.

    Fields:
        user_id: The user this activity belongs to.
        date: The calendar date (stored as midnight UTC datetime).
        actions: List of actions completed today.
        streak_count: Current consecutive-day streak (updated by StreakService).
        total_xp: Sum of all xp_earned from actions today.
        current_league: League tier (bronze/silver/gold/platinum/diamond).
        streak_freeze_available: Whether a streak freeze can be used.
        freeze_count: Number of banked streak freezes (max 3).
        week_start_xp: Weekly XP accumulator for league calculation.
    """

    user_id: Indexed(PydanticObjectId)
    date: datetime
    actions: list[ActivityEntry] = Field(default_factory=list)
    streak_count: int = 0
    total_xp: int = 0
    current_league: str = "bronze"
    streak_freeze_available: bool = True
    freeze_count: int = 0
    week_start_xp: int = 0

    class Settings:
        name = "user_activities"
        indexes = [
            IndexModel(
                [("user_id", 1), ("date", 1)],
                unique=True,
            ),
        ]
