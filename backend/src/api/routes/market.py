"""Market intelligence routes — signals, company trajectory, and disruption radar."""

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.db.documents.user import User
from src.repositories.market_signal_repository import MarketSignalRepository
from src.services.market_signal_service import (
    classify_signal,
    detect_disruptions,
    predict_company_trajectory,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/market", tags=["market"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MarketSignalResponse(BaseModel):
    id: str
    signal_type: str
    severity: str
    title: str
    description: str
    industry: str
    region: str
    confidence: float
    tags: list[str] = Field(default_factory=list)


class CompanyTrajectoryRequest(BaseModel):
    company_name: str
    industry: str = ""


class CompanyTrajectoryResponse(BaseModel):
    company_name: str
    trajectory: str
    confidence: float
    signals: list[str] = Field(default_factory=list)
    recommendation: str = ""


class DisruptionIndicatorResponse(BaseModel):
    industry: str
    disruption_type: str
    impact_level: str
    description: str
    affected_roles: list[str] = Field(default_factory=list)
    timeline: str = ""


class DisruptionRadarRequest(BaseModel):
    industry: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/signals", response_model=list[MarketSignalResponse])
async def get_market_signals(
    signal_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> list[MarketSignalResponse]:
    """Get market signals relevant to the authenticated user."""
    repo = MarketSignalRepository()
    signals = await repo.get_for_user(user.id, signal_type=signal_type, limit=limit)

    return [
        MarketSignalResponse(
            id=str(s.id),
            signal_type=s.signal_type,
            severity=s.severity,
            title=s.title,
            description=s.description,
            industry=s.industry,
            region=s.region,
            confidence=s.confidence,
            tags=s.tags,
        )
        for s in signals
    ]


@router.post("/company-trajectory", response_model=CompanyTrajectoryResponse)
async def get_company_trajectory(
    request: CompanyTrajectoryRequest,
    user: User = Depends(get_current_user),
) -> CompanyTrajectoryResponse:
    """Predict a company's trajectory based on market signals."""
    repo = MarketSignalRepository()
    signals = await repo.get_by_industry(request.industry, limit=50)

    # Prioritize signals mentioning the company, include industry signals as context
    company_lower = request.company_name.lower()
    signal_dicts = [
        {
            "signal_type": s.signal_type,
            "severity": s.severity,
            "title": s.title,
            "description": s.description,
        }
        for s in signals
        if company_lower in s.title.lower()
        or company_lower in s.description.lower()
        or not request.company_name  # include all if no company filter
    ]
    # Fall back to all industry signals if no company-specific matches
    if not signal_dicts:
        signal_dicts = [
            {
                "signal_type": s.signal_type,
                "severity": s.severity,
                "title": s.title,
                "description": s.description,
            }
            for s in signals
        ]

    trajectory = predict_company_trajectory(request.company_name, signal_dicts)

    return CompanyTrajectoryResponse(
        company_name=trajectory.company_name,
        trajectory=trajectory.trajectory,
        confidence=trajectory.confidence,
        signals=trajectory.signals,
        recommendation=trajectory.recommendation,
    )


@router.post("/disruption-radar", response_model=list[DisruptionIndicatorResponse])
async def get_disruption_radar(
    request: DisruptionRadarRequest,
    user: User = Depends(get_current_user),
) -> list[DisruptionIndicatorResponse]:
    """Detect industry disruption signals."""
    repo = MarketSignalRepository()
    signals = await repo.get_by_industry(request.industry, limit=50)

    signal_dicts = [
        {
            "signal_type": s.signal_type,
            "severity": s.severity,
            "title": s.title,
            "description": s.description,
        }
        for s in signals
    ]

    disruptions = detect_disruptions(request.industry, signal_dicts)

    return [
        DisruptionIndicatorResponse(
            industry=d.industry,
            disruption_type=d.disruption_type,
            impact_level=d.impact_level,
            description=d.description,
            affected_roles=d.affected_roles,
            timeline=d.timeline,
        )
        for d in disruptions
    ]
