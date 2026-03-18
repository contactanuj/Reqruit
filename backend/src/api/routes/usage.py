"""Usage dashboard API — user-facing LLM usage summary and breakdown."""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.db.documents.usage_ledger import UsageTier
from src.db.documents.user import User
from src.services.usage_service import UsageService

logger = structlog.get_logger()

router = APIRouter(prefix="/usage", tags=["usage"])


# ── Response schemas ─────────────────────────────────────────────────────


class PeriodUsageResponse(BaseModel):
    total_tokens: int
    total_cost_usd: float


class UsageSummaryResponse(BaseModel):
    daily: PeriodUsageResponse
    weekly: PeriodUsageResponse
    monthly: PeriodUsageResponse
    tier: str
    tier_limit_usd: float
    tier_limit_tokens: int
    usage_percentage: float


class UsageBreakdownResponse(BaseModel):
    breakdown_by_feature: dict[str, float]
    breakdown_by_model: dict[str, float]
    period_start: datetime
    period_end: datetime


# ── Dependency ───────────────────────────────────────────────────────────


def _get_usage_service() -> UsageService:
    from src.core.config import get_settings
    from src.repositories.usage_ledger_repository import UsageLedgerRepository

    settings = get_settings()
    return UsageService(repo=UsageLedgerRepository(), tier_settings=settings.tier)


def _resolve_user_tier(user: User) -> UsageTier:
    """Derive the user's tier from their profile (not from stale ledger data)."""
    if getattr(user, "is_admin", False):
        return UsageTier.ADMIN
    if getattr(user, "usage_tier", None) == "pro":
        return UsageTier.PRO
    return UsageTier.FREE


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get("/me", response_model=UsageSummaryResponse)
async def get_my_usage(
    user: User = Depends(get_current_user),
    service: UsageService = Depends(_get_usage_service),
):
    """Return the current user's usage summary across daily/weekly/monthly."""
    user_tier = _resolve_user_tier(user)
    summary = await service.get_usage_summary(user.id, user_tier)

    logger.info("usage_summary_requested", user_id=str(user.id))

    return UsageSummaryResponse(
        daily=PeriodUsageResponse(
            total_tokens=summary.daily.total_tokens,
            total_cost_usd=summary.daily.total_cost_usd,
        ),
        weekly=PeriodUsageResponse(
            total_tokens=summary.weekly.total_tokens,
            total_cost_usd=summary.weekly.total_cost_usd,
        ),
        monthly=PeriodUsageResponse(
            total_tokens=summary.monthly.total_tokens,
            total_cost_usd=summary.monthly.total_cost_usd,
        ),
        tier=summary.tier,
        tier_limit_usd=summary.tier_limit_usd,
        tier_limit_tokens=summary.tier_limit_tokens,
        usage_percentage=summary.usage_percentage,
    )


@router.get("/me/breakdown", response_model=UsageBreakdownResponse)
async def get_my_usage_breakdown(
    user: User = Depends(get_current_user),
    service: UsageService = Depends(_get_usage_service),
):
    """Return per-feature and per-model cost breakdown for the current week."""
    breakdown = await service.get_usage_breakdown(user.id)

    logger.info("usage_breakdown_requested", user_id=str(user.id))

    return UsageBreakdownResponse(
        breakdown_by_feature=breakdown.breakdown_by_feature,
        breakdown_by_model=breakdown.breakdown_by_model,
        period_start=breakdown.period_start,
        period_end=breakdown.period_end,
    )
