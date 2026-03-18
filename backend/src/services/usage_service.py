"""UsageService — user-facing LLM usage summary, breakdown, tier enforcement, and admin analytics."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.core.config import TierSettings
from src.core.exceptions import (
    DailyCapReachedError,
    NotFoundError,
    TierLimitExceededError,
)
from src.db.documents.usage_ledger import UsagePeriod, UsageTier
from src.db.documents.user import User
from src.repositories.usage_ledger_repository import (
    UsageLedgerRepository,
    _compute_period_start,
    _resolve_tier_limits,
)

logger = structlog.get_logger()


class PeriodUsage(BaseModel):
    """Token and cost totals for a single period."""

    total_tokens: int = 0
    total_cost_usd: float = 0.0


class UsageSummary(BaseModel):
    """Full usage summary across daily/weekly/monthly periods."""

    daily: PeriodUsage
    weekly: PeriodUsage
    monthly: PeriodUsage
    tier: str
    tier_limit_usd: float
    tier_limit_tokens: int
    usage_percentage: float


class UsageBreakdown(BaseModel):
    """Per-feature and per-model cost breakdown for a period."""

    breakdown_by_feature: dict[str, float]
    breakdown_by_model: dict[str, float]
    period_start: datetime
    period_end: datetime


class AdminUsageSummary(BaseModel):
    """Aggregate usage metrics across all users for admin dashboard."""

    total_cost_this_week: float
    per_user_average_usd: float
    model_routing_distribution: dict[str, float]
    user_count_by_tier: dict[str, int]
    period_start: datetime
    period_end: datetime


class UsageAnomaly(BaseModel):
    """A user with anomalous usage patterns."""

    user_id: str
    current_week_cost: float
    rolling_avg_cost: float
    spike_multiplier: float
    anomaly_type: str  # "cost_spike" or "frequency_spike"


class TierChangeResult(BaseModel):
    """Result of an admin tier change operation."""

    user_id: str
    previous_tier: str
    new_tier: str
    effective_immediately: bool = True


class UsageService:
    """Stateless service for querying user LLM usage data."""

    def __init__(
        self, repo: UsageLedgerRepository, tier_settings: TierSettings
    ) -> None:
        self._repo = repo
        self._tier_settings = tier_settings

    async def get_usage_summary(
        self, user_id: PydanticObjectId, user_tier: UsageTier
    ) -> UsageSummary:
        """Fetch daily/weekly/monthly usage and compute usage percentage."""
        daily = await self._repo.get_current_usage(user_id, UsagePeriod.DAILY)
        weekly = await self._repo.get_current_usage(user_id, UsagePeriod.WEEKLY)
        monthly = await self._repo.get_current_usage(user_id, UsagePeriod.MONTHLY)

        tier_limit_usd, tier_limit_tokens = _resolve_tier_limits(
            user_tier, self._tier_settings
        )

        weekly_cost = weekly.total_cost_usd if weekly else 0.0
        usage_pct = (weekly_cost / tier_limit_usd * 100) if tier_limit_usd > 0 else 0.0

        logger.debug(
            "usage_summary_fetched",
            user_id=str(user_id),
            tier=user_tier.value,
            usage_percentage=round(usage_pct, 2),
        )

        return UsageSummary(
            daily=PeriodUsage(
                total_tokens=daily.total_tokens if daily else 0,
                total_cost_usd=daily.total_cost_usd if daily else 0.0,
            ),
            weekly=PeriodUsage(
                total_tokens=weekly.total_tokens if weekly else 0,
                total_cost_usd=weekly.total_cost_usd if weekly else 0.0,
            ),
            monthly=PeriodUsage(
                total_tokens=monthly.total_tokens if monthly else 0,
                total_cost_usd=monthly.total_cost_usd if monthly else 0.0,
            ),
            tier=user_tier.value,
            tier_limit_usd=tier_limit_usd,
            tier_limit_tokens=tier_limit_tokens,
            usage_percentage=round(usage_pct, 2),
        )

    async def get_usage_breakdown(
        self, user_id: PydanticObjectId
    ) -> UsageBreakdown:
        """Fetch weekly per-feature and per-model cost breakdown."""
        weekly = await self._repo.get_current_usage(user_id, UsagePeriod.WEEKLY)

        period_start = _compute_period_start(UsagePeriod.WEEKLY)
        period_end = datetime.now(UTC)

        logger.debug(
            "usage_breakdown_fetched",
            user_id=str(user_id),
            has_data=weekly is not None,
        )

        return UsageBreakdown(
            breakdown_by_feature=weekly.breakdown_by_feature if weekly else {},
            breakdown_by_model=weekly.breakdown_by_model if weekly else {},
            period_start=period_start,
            period_end=period_end,
        )

    async def enforce_tier_limit(
        self, user_id: PydanticObjectId, user_tier: UsageTier
    ) -> None:
        """Check tier and daily limits; raise on violation. Fail-open on DB errors."""
        if user_tier == UsageTier.ADMIN:
            return

        try:
            tier_limit_usd, tier_limit_tokens = _resolve_tier_limits(
                user_tier, self._tier_settings
            )

            # Weekly tier check
            weekly = await self._repo.get_current_usage(user_id, UsagePeriod.WEEKLY)
            weekly_cost = weekly.total_cost_usd if weekly else 0.0
            weekly_tokens = weekly.total_tokens if weekly else 0

            if weekly_cost >= tier_limit_usd or weekly_tokens >= tier_limit_tokens:
                raise TierLimitExceededError(
                    tier_name=user_tier.value.upper(),
                    current_usage_usd=weekly_cost,
                    limit_usd=tier_limit_usd,
                    current_tokens=weekly_tokens,
                    limit_tokens=tier_limit_tokens,
                )

            # Daily cap check (weekly_limit / 5 business days)
            daily_cap_usd = tier_limit_usd / 5
            daily = await self._repo.get_current_usage(user_id, UsagePeriod.DAILY)
            daily_cost = daily.total_cost_usd if daily else 0.0

            if daily_cost >= daily_cap_usd:
                now = datetime.now(UTC)
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                raise DailyCapReachedError(
                    daily_cost_usd=daily_cost,
                    daily_cap_usd=daily_cap_usd,
                    resets_at=tomorrow,
                )

            logger.debug(
                "tier_enforcement_allowed",
                user_id=str(user_id),
                tier=user_tier.value,
                weekly_cost=weekly_cost,
                daily_cost=daily_cost,
            )

        except (TierLimitExceededError, DailyCapReachedError):
            raise
        except Exception:
            logger.warning(
                "tier_enforcement_failed_open",
                user_id=str(user_id),
                exc_info=True,
            )

    # -- Admin analytics ------------------------------------------------------

    async def get_admin_summary(self) -> AdminUsageSummary:
        """Aggregate usage across all users for the current week."""
        week_start = _compute_period_start(UsagePeriod.WEEKLY)
        weekly_entries = await self._repo.get_all_weekly_entries(week_start)

        total_cost = sum(e.total_cost_usd for e in weekly_entries)
        user_count = len(weekly_entries)
        per_user_avg = total_cost / user_count if user_count > 0 else 0.0

        model_dist = self._compute_model_distribution(weekly_entries)
        tier_counts = self._count_users_by_tier(weekly_entries)

        logger.info(
            "admin_summary_fetched",
            total_cost=round(total_cost, 4),
            user_count=user_count,
        )

        return AdminUsageSummary(
            total_cost_this_week=round(total_cost, 4),
            per_user_average_usd=round(per_user_avg, 4),
            model_routing_distribution=model_dist,
            user_count_by_tier=tier_counts,
            period_start=week_start,
            period_end=datetime.now(UTC),
        )

    async def get_usage_anomalies(self) -> list[UsageAnomaly]:
        """Detect users with anomalous usage patterns this week."""
        week_start = _compute_period_start(UsagePeriod.WEEKLY)
        active_user_ids = await self._repo.get_all_active_user_ids_this_week(
            week_start
        )
        anomalies: list[UsageAnomaly] = []

        for user_id in active_user_ids:
            current = await self._repo.get_current_usage(
                user_id, UsagePeriod.WEEKLY
            )
            if not current:
                continue

            history = await self._repo.get_user_weekly_history(user_id, weeks=4)
            # Exclude current week from history (it may appear in results)
            history = [
                h for h in history if h.period_start != week_start
            ]
            if not history:
                continue

            avg_cost, avg_tokens = self._compute_rolling_average(history)

            if avg_cost > 0 and current.total_cost_usd > avg_cost * 3:
                anomalies.append(UsageAnomaly(
                    user_id=str(user_id),
                    current_week_cost=current.total_cost_usd,
                    rolling_avg_cost=avg_cost,
                    spike_multiplier=round(current.total_cost_usd / avg_cost, 2),
                    anomaly_type="cost_spike",
                ))
            elif avg_tokens > 0 and current.total_tokens > avg_tokens * 2:
                anomalies.append(UsageAnomaly(
                    user_id=str(user_id),
                    current_week_cost=current.total_cost_usd,
                    rolling_avg_cost=avg_cost,
                    spike_multiplier=round(current.total_tokens / avg_tokens, 2),
                    anomaly_type="frequency_spike",
                ))

        logger.info("anomaly_detection_completed", anomaly_count=len(anomalies))
        return anomalies

    async def update_user_tier(
        self,
        user_id: PydanticObjectId,
        new_tier: UsageTier,
        admin_user_id: PydanticObjectId,
    ) -> TierChangeResult:
        """Update a user's tier. Returns previous and new tier."""

        user = await User.get(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))

        previous_tier = self._derive_tier(user)
        self._apply_tier(user, new_tier)
        await user.save()

        logger.info(
            "tier_updated",
            admin_user_id=str(admin_user_id),
            target_user_id=str(user_id),
            previous_tier=previous_tier.value,
            new_tier=new_tier.value,
        )

        return TierChangeResult(
            user_id=str(user_id),
            previous_tier=previous_tier.value,
            new_tier=new_tier.value,
        )

    @staticmethod
    def _derive_tier(user: object) -> UsageTier:
        """Derive UsageTier from user flags."""
        if getattr(user, "is_admin", False):
            return UsageTier.ADMIN
        if getattr(user, "usage_tier", None) == UsageTier.PRO.value:
            return UsageTier.PRO
        return UsageTier.FREE

    @staticmethod
    def _apply_tier(user: object, tier: UsageTier) -> None:
        """Apply tier changes to user model fields."""
        if tier == UsageTier.ADMIN:
            user.is_admin = True  # type: ignore[attr-defined]
        else:
            user.is_admin = False  # type: ignore[attr-defined]
        user.usage_tier = tier.value  # type: ignore[attr-defined]

    @staticmethod
    def _compute_model_distribution(
        weekly_entries: list,
    ) -> dict[str, float]:
        """Merge model breakdowns and convert to percentage distribution."""
        totals: dict[str, float] = defaultdict(float)
        for entry in weekly_entries:
            for model, cost in (entry.breakdown_by_model or {}).items():
                totals[model] += cost

        grand_total = sum(totals.values())
        if grand_total <= 0:
            return {}
        return {
            model: round(cost / grand_total * 100, 1)
            for model, cost in totals.items()
        }

    @staticmethod
    def _count_users_by_tier(weekly_entries: list) -> dict[str, int]:
        """Count unique users per tier from weekly entries."""
        counts: dict[str, int] = defaultdict(int)
        for entry in weekly_entries:
            tier_val = entry.tier if isinstance(entry.tier, str) else entry.tier.value
            counts[tier_val.upper()] += 1
        return dict(counts)

    @staticmethod
    def _compute_rolling_average(
        history: list,
    ) -> tuple[float, float]:
        """Return (avg_cost, avg_tokens) from historical weekly entries."""
        if not history:
            return 0.0, 0.0
        total_cost = sum(e.total_cost_usd for e in history)
        total_tokens = sum(e.total_tokens for e in history)
        n = len(history)
        return total_cost / n, total_tokens / n
