"""
Discovery routes — job discovery preferences and daily shortlists.

Routes:
    PUT  /discovery/preferences  — Update discovery preferences
    GET  /discovery/preferences  — Get current preferences
    GET  /discovery/shortlist    — Get latest daily shortlist
    GET  /discovery/history      — Get shortlist history
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user, get_discovery_service
from src.core.exceptions import NotFoundError
from src.db.documents.user import User
from src.services.job_discovery_service import JobDiscoveryService

router = APIRouter(prefix="/discovery", tags=["discovery"])


# ── Request/Response schemas ──────────────────────────────────────────


class DiscoveryPreferencesRequest(BaseModel):
    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    salary_min: int = 0
    salary_max: int = 0
    company_sizes: list[str] = Field(default_factory=list)
    remote_only: bool = False


class DiscoveryPreferencesResponse(BaseModel):
    roles: list[str]
    locations: list[str]
    salary_min: int
    salary_max: int
    company_sizes: list[str]
    remote_only: bool


class ShortlistJobResponse(BaseModel):
    job_id: str | None = None
    source: str = ""
    source_url: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    fit_score: float = 0.0
    roi_prediction: str = ""
    trust_score: float | None = None
    salary_range: str = ""
    match_reasons: list[str] = Field(default_factory=list)


class ShortlistResponse(BaseModel):
    date: str
    jobs: list[ShortlistJobResponse]
    generation_cost_usd: float = 0.0


# ── Routes ────────────────────────────────────────────────────────────


@router.put("/preferences", response_model=DiscoveryPreferencesResponse)
async def update_preferences(
    body: DiscoveryPreferencesRequest,
    user: User = Depends(get_current_user),
    service: JobDiscoveryService = Depends(get_discovery_service),
):
    """Update the user's job discovery preferences."""
    from src.db.documents.job_shortlist import DiscoveryPreferences

    prefs = DiscoveryPreferences(**body.model_dump())
    try:
        saved = await service.update_preferences(user.id, prefs)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc
    return DiscoveryPreferencesResponse(**saved.model_dump())


@router.get("/preferences", response_model=DiscoveryPreferencesResponse | None)
async def get_preferences(
    user: User = Depends(get_current_user),
    service: JobDiscoveryService = Depends(get_discovery_service),
):
    """Get the user's current discovery preferences."""
    prefs = await service.get_preferences(user.id)
    if prefs is None:
        return None
    return DiscoveryPreferencesResponse(**prefs.model_dump())


@router.get("/shortlist", response_model=ShortlistResponse | None)
async def get_shortlist(
    user: User = Depends(get_current_user),
    service: JobDiscoveryService = Depends(get_discovery_service),
):
    """Get the latest daily job shortlist."""
    shortlist = await service.get_latest_shortlist(user.id)
    if shortlist is None:
        return None
    return ShortlistResponse(
        date=shortlist.date.isoformat(),
        jobs=[
            ShortlistJobResponse(
                job_id=str(j.job_id) if j.job_id else None,
                source=j.source,
                source_url=j.source_url,
                title=j.title,
                company=j.company,
                location=j.location,
                fit_score=j.fit_score,
                roi_prediction=j.roi_prediction,
                trust_score=j.trust_score,
                salary_range=j.salary_range,
                match_reasons=j.match_reasons,
            )
            for j in shortlist.jobs
        ],
        generation_cost_usd=shortlist.generation_cost_usd,
    )


@router.get("/history", response_model=list[ShortlistResponse])
async def get_history(
    user: User = Depends(get_current_user),
    service: JobDiscoveryService = Depends(get_discovery_service),
):
    """Get shortlist history (last 7 days)."""
    shortlists = await service.get_shortlist_history(user.id)
    return [
        ShortlistResponse(
            date=s.date.isoformat(),
            jobs=[
                ShortlistJobResponse(
                    job_id=str(j.job_id) if j.job_id else None,
                    source=j.source,
                    source_url=j.source_url,
                    title=j.title,
                    company=j.company,
                    location=j.location,
                    fit_score=j.fit_score,
                    roi_prediction=j.roi_prediction,
                    trust_score=j.trust_score,
                    salary_range=j.salary_range,
                    match_reasons=j.match_reasons,
                )
                for j in s.jobs
            ],
            generation_cost_usd=s.generation_cost_usd,
        )
        for s in shortlists
    ]
