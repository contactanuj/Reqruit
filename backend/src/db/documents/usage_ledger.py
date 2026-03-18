"""
UsageLedger document — per-user LLM cost attribution with period-based rollups.

Each entry tracks token usage and cost for a user within a time period
(daily, weekly, or monthly). Daily entries are updated in real-time via
atomic $inc operations. Weekly and monthly entries are aggregated by a
periodic Celery Beat task.
"""

from datetime import datetime
from enum import StrEnum

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class UsagePeriod(StrEnum):
    """Time period for usage aggregation."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class UsageTier(StrEnum):
    """User tier determining usage limits."""

    FREE = "free"
    PRO = "pro"
    ADMIN = "admin"


class UsageLedger(TimestampedDocument):
    """
    Per-user LLM usage and cost tracking within a time period.

    Fields:
        user_id: The user this ledger entry belongs to.
        period: Time granularity (daily/weekly/monthly).
        period_start: UTC start of the period (midnight for daily, Monday for weekly, 1st for monthly).
        total_tokens: Cumulative token count for this period.
        total_cost_usd: Cumulative cost in USD.
        breakdown_by_feature: Cost attributed to each feature category.
        breakdown_by_model: Cost attributed to each LLM model.
        tier: User's tier at the time of creation.
        tier_limit_usd: Cost cap for this tier/period.
        tier_limit_tokens: Token cap for this tier/period.
    """

    user_id: PydanticObjectId
    period: UsagePeriod
    period_start: datetime
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    breakdown_by_feature: dict[str, float] = Field(default_factory=dict)
    breakdown_by_model: dict[str, float] = Field(default_factory=dict)
    tier: UsageTier = UsageTier.FREE
    tier_limit_usd: float = 1.50
    tier_limit_tokens: int = 500_000

    class Settings:
        name = "usage_ledgers"
        indexes = [
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("period", ASCENDING),
                    ("period_start", ASCENDING),
                ],
                unique=True,
            ),
        ]
