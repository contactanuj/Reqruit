"""Repository for UsageLedger documents — per-user cost attribution queries."""

from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId
from pymongo import ReturnDocument

from src.core.config import TierSettings
from src.db.documents.usage_ledger import UsageLedger, UsagePeriod, UsageTier
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


def _compute_period_start(period: UsagePeriod) -> datetime:
    """Compute the start of the current period in UTC."""
    now = datetime.now(UTC)
    if period == UsagePeriod.DAILY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == UsagePeriod.WEEKLY:
        # Monday 00:00 UTC of current ISO week
        monday = now - timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monthly: 1st of the month
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _resolve_tier_limits(
    tier: UsageTier, tier_settings: TierSettings
) -> tuple[float, int]:
    """Return (limit_usd, limit_tokens) for a given tier."""
    if tier == UsageTier.ADMIN:
        return 999999.0, 999_999_999
    if tier == UsageTier.PRO:
        return tier_settings.pro_weekly_cost_usd, tier_settings.pro_weekly_tokens
    return tier_settings.free_weekly_cost_usd, tier_settings.free_weekly_tokens


class UsageLedgerRepository(BaseRepository[UsageLedger]):
    """Data access for per-user LLM usage tracking."""

    def __init__(self) -> None:
        super().__init__(UsageLedger)

    async def increment_usage(
        self,
        user_id: PydanticObjectId,
        tokens: int,
        cost_usd: float,
        feature: str,
        model_name: str,
        tier: UsageTier,
        tier_settings: TierSettings,
    ) -> UsageLedger:
        """
        Atomically increment daily usage for a user via upsert.

        Creates the daily entry if it doesn't exist ($setOnInsert), then
        atomically increments token/cost counters and feature/model breakdowns.
        """
        period_start = _compute_period_start(UsagePeriod.DAILY)
        tier_limit_usd, tier_limit_tokens = _resolve_tier_limits(tier, tier_settings)

        result = await UsageLedger.get_motor_collection().find_one_and_update(
            {
                "user_id": user_id,
                "period": UsagePeriod.DAILY.value,
                "period_start": period_start,
            },
            {
                "$inc": {
                    "total_tokens": tokens,
                    "total_cost_usd": cost_usd,
                    f"breakdown_by_feature.{feature.replace('.', '_')}": cost_usd,
                    f"breakdown_by_model.{model_name.replace('.', '_')}": cost_usd,
                },
                "$setOnInsert": {
                    "tier": tier.value,
                    "tier_limit_usd": tier_limit_usd,
                    "tier_limit_tokens": tier_limit_tokens,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        logger.debug(
            "usage_incremented",
            user_id=str(user_id),
            tokens=tokens,
            cost_usd=cost_usd,
            feature=feature,
        )

        return UsageLedger.model_validate(result)

    async def get_current_usage(
        self, user_id: PydanticObjectId, period: UsagePeriod
    ) -> UsageLedger | None:
        """Get the current period's usage entry for a user."""
        period_start = _compute_period_start(period)
        return await self.find_one({
            "user_id": user_id,
            "period": period.value,
            "period_start": period_start,
        })

    async def get_daily_entries_for_period(
        self, user_id: PydanticObjectId, start: datetime, end: datetime
    ) -> list[UsageLedger]:
        """Return all daily entries for a user within a date range."""
        return await self.find_many(
            filters={
                "user_id": user_id,
                "period": UsagePeriod.DAILY.value,
                "period_start": {"$gte": start, "$lte": end},
            },
            skip=0,
            limit=31,  # max days in a month
            sort="-period_start",
        )

    async def upsert_rollup(
        self,
        user_id: PydanticObjectId,
        period: UsagePeriod,
        period_start: datetime,
        total_tokens: int,
        total_cost_usd: float,
        breakdown_by_feature: dict[str, float],
        breakdown_by_model: dict[str, float],
        tier: UsageTier,
        tier_limit_usd: float,
        tier_limit_tokens: int,
    ) -> UsageLedger:
        """Upsert a weekly or monthly rollup entry."""
        result = await UsageLedger.get_motor_collection().find_one_and_update(
            {
                "user_id": user_id,
                "period": period.value,
                "period_start": period_start,
            },
            {
                "$set": {
                    "total_tokens": total_tokens,
                    "total_cost_usd": total_cost_usd,
                    "breakdown_by_feature": breakdown_by_feature,
                    "breakdown_by_model": breakdown_by_model,
                    "tier": tier.value,
                    "tier_limit_usd": tier_limit_usd,
                    "tier_limit_tokens": tier_limit_tokens,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return UsageLedger.model_validate(result)

    async def get_distinct_user_ids_in_range(
        self, start: datetime, end: datetime
    ) -> list[PydanticObjectId]:
        """Get distinct user_ids with daily entries in a date range."""
        collection = UsageLedger.get_motor_collection()
        result = await collection.distinct(
            "user_id",
            {
                "period": UsagePeriod.DAILY.value,
                "period_start": {"$gte": start, "$lte": end},
            },
        )
        return result

    # -- Admin queries --------------------------------------------------------

    async def get_all_weekly_entries(
        self, period_start: datetime
    ) -> list[UsageLedger]:
        """Return all weekly UsageLedger entries for a given week start."""
        return await self.find_many(
            filters={
                "period": UsagePeriod.WEEKLY.value,
                "period_start": period_start,
            },
            skip=0,
            limit=10_000,
        )

    async def get_user_weekly_history(
        self, user_id: PydanticObjectId, weeks: int = 4
    ) -> list[UsageLedger]:
        """Return the most recent N weekly entries for a user, descending."""
        return await self.find_many(
            filters={
                "user_id": user_id,
                "period": UsagePeriod.WEEKLY.value,
            },
            skip=0,
            limit=weeks,
            sort="-period_start",
        )

    async def get_all_active_user_ids_this_week(
        self, period_start: datetime
    ) -> list[PydanticObjectId]:
        """Return distinct user_ids with weekly entries for the given week."""
        collection = UsageLedger.get_motor_collection()
        return await collection.distinct(
            "user_id",
            {
                "period": UsagePeriod.WEEKLY.value,
                "period_start": period_start,
            },
        )
