"""
Admin endpoints for usage analytics and tier management.

Endpoints
---------
    GET  /admin/usage/summary      Aggregate LLM cost metrics across all users
    GET  /admin/usage/anomalies    Detect usage spikes and anomalous patterns
    PUT  /admin/tiers/{user_id}    Override a user's usage tier
"""

from datetime import datetime

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_admin_user, get_usage_service
from src.db.documents.usage_ledger import UsageTier
from src.db.documents.user import User
from src.services.usage_service import UsageService

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin-usage"])


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------


class AdminUsageSummaryResponse(BaseModel):
    total_cost_this_week: float
    per_user_average_usd: float
    model_routing_distribution: dict[str, float]
    user_count_by_tier: dict[str, int]
    period_start: datetime
    period_end: datetime


class UsageAnomalyResponse(BaseModel):
    user_id: str
    current_week_cost: float
    rolling_avg_cost: float
    spike_multiplier: float
    anomaly_type: str


class TierUpdateRequest(BaseModel):
    tier: UsageTier


class TierUpdateResponse(BaseModel):
    user_id: str
    previous_tier: str
    new_tier: str
    effective_immediately: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/usage/summary",
    response_model=AdminUsageSummaryResponse,
    summary="Aggregate usage summary",
)
async def admin_usage_summary(
    _admin: User = Depends(get_current_admin_user),
    service: UsageService = Depends(get_usage_service),
):
    """Return aggregate LLM cost metrics for the current week."""
    summary = await service.get_admin_summary()
    return AdminUsageSummaryResponse(
        total_cost_this_week=summary.total_cost_this_week,
        per_user_average_usd=summary.per_user_average_usd,
        model_routing_distribution=summary.model_routing_distribution,
        user_count_by_tier=summary.user_count_by_tier,
        period_start=summary.period_start,
        period_end=summary.period_end,
    )


@router.get(
    "/usage/anomalies",
    response_model=list[UsageAnomalyResponse],
    summary="Detect usage anomalies",
)
async def admin_usage_anomalies(
    _admin: User = Depends(get_current_admin_user),
    service: UsageService = Depends(get_usage_service),
):
    """Return users with anomalous usage spikes this week."""
    anomalies = await service.get_usage_anomalies()
    return [
        UsageAnomalyResponse(
            user_id=a.user_id,
            current_week_cost=a.current_week_cost,
            rolling_avg_cost=a.rolling_avg_cost,
            spike_multiplier=a.spike_multiplier,
            anomaly_type=a.anomaly_type,
        )
        for a in anomalies
    ]


@router.put(
    "/tiers/{user_id}",
    response_model=TierUpdateResponse,
    summary="Update user tier",
)
async def update_user_tier(
    user_id: PydanticObjectId,
    body: TierUpdateRequest,
    admin: User = Depends(get_current_admin_user),
    service: UsageService = Depends(get_usage_service),
):
    """Override a user's usage tier (FREE, PRO, ADMIN)."""
    result = await service.update_user_tier(user_id, body.tier, admin.id)

    logger.info(
        "admin_tier_update",
        admin_id=str(admin.id),
        target_user_id=str(user_id),
        new_tier=body.tier.value,
    )

    return TierUpdateResponse(
        user_id=result.user_id,
        previous_tier=result.previous_tier,
        new_tier=result.new_tier,
        effective_immediately=result.effective_immediately,
    )
