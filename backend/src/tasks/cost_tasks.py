"""Celery Beat task for periodic UsageLedger rollup aggregation."""

from collections import defaultdict
from datetime import UTC, datetime

import structlog
from celery import shared_task

from src.tasks.base import BaseTask, _run_async

logger = structlog.get_logger()


def _merge_breakdowns(
    entries_breakdowns: list[dict[str, float]],
) -> dict[str, float]:
    """Merge multiple breakdown dicts by summing values per key."""
    merged: dict[str, float] = defaultdict(float)
    for breakdown in entries_breakdowns:
        for key, value in breakdown.items():
            merged[key] += value
    return dict(merged)


@shared_task(bind=True, base=BaseTask, name="tasks.batch.aggregate_usage_rollups")
def aggregate_usage_rollups(self):
    """
    Periodic task that aggregates daily UsageLedger entries into weekly
    and monthly rollups.

    Runs every 15 minutes via Celery Beat. This is an internal aggregation
    task — it does NOT create a TaskRecord.
    """
    from src.db.documents.usage_ledger import UsagePeriod
    from src.repositories.usage_ledger_repository import (
        UsageLedgerRepository,
        _compute_period_start,
        _resolve_tier_limits,
    )

    async def _aggregate():
        repo = UsageLedgerRepository()
        now = datetime.now(UTC)
        week_start = _compute_period_start(UsagePeriod.WEEKLY)
        month_start = _compute_period_start(UsagePeriod.MONTHLY)

        # Get all users with daily entries this week
        user_ids = await repo.get_distinct_user_ids_in_range(week_start, now)

        logger.info(
            "usage_rollup_started",
            user_count=len(user_ids),
            week_start=str(week_start),
            month_start=str(month_start),
        )

        for user_id in user_ids:
            # Weekly rollup
            weekly_entries = await repo.get_daily_entries_for_period(
                user_id, week_start, now
            )
            if weekly_entries:
                total_tokens = sum(e.total_tokens for e in weekly_entries)
                total_cost = sum(e.total_cost_usd for e in weekly_entries)
                feature_breakdown = _merge_breakdowns(
                    [e.breakdown_by_feature for e in weekly_entries]
                )
                model_breakdown = _merge_breakdowns(
                    [e.breakdown_by_model for e in weekly_entries]
                )
                # Use the tier from the most recent entry
                latest = weekly_entries[0]
                from src.core.config import get_settings

                settings = get_settings()
                tier_limit_usd, tier_limit_tokens = _resolve_tier_limits(
                    latest.tier, settings.tier
                )
                await repo.upsert_rollup(
                    user_id=user_id,
                    period=UsagePeriod.WEEKLY,
                    period_start=week_start,
                    total_tokens=total_tokens,
                    total_cost_usd=total_cost,
                    breakdown_by_feature=feature_breakdown,
                    breakdown_by_model=model_breakdown,
                    tier=latest.tier,
                    tier_limit_usd=tier_limit_usd,
                    tier_limit_tokens=tier_limit_tokens,
                )

            # Monthly rollup
            monthly_entries = await repo.get_daily_entries_for_period(
                user_id, month_start, now
            )
            if monthly_entries:
                total_tokens = sum(e.total_tokens for e in monthly_entries)
                total_cost = sum(e.total_cost_usd for e in monthly_entries)
                feature_breakdown = _merge_breakdowns(
                    [e.breakdown_by_feature for e in monthly_entries]
                )
                model_breakdown = _merge_breakdowns(
                    [e.breakdown_by_model for e in monthly_entries]
                )
                latest = monthly_entries[0]
                tier_limit_usd, tier_limit_tokens = _resolve_tier_limits(
                    latest.tier, settings.tier
                )
                await repo.upsert_rollup(
                    user_id=user_id,
                    period=UsagePeriod.MONTHLY,
                    period_start=month_start,
                    total_tokens=total_tokens,
                    total_cost_usd=total_cost,
                    breakdown_by_feature=feature_breakdown,
                    breakdown_by_model=model_breakdown,
                    tier=latest.tier,
                    tier_limit_usd=tier_limit_usd,
                    tier_limit_tokens=tier_limit_tokens,
                )

        logger.info(
            "usage_rollup_completed",
            user_count=len(user_ids),
        )

    return _run_async(_aggregate())
