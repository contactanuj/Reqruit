"""
Admin discovery routes — source health monitoring and data freshness dashboard.

Routes:
    GET  /admin/discovery/sources/health — View all source health statuses
    POST /admin/discovery/sources/{name}/toggle — Enable/disable a source
    GET  /admin/discovery/cache/analytics — JD cache cost analytics
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_admin_user
from src.core.exceptions import NotFoundError
from src.db.documents.user import User
from src.repositories.data_source_health_repository import DataSourceHealthRepository
from src.repositories.jd_cache_repository import JDCacheRepository

router = APIRouter(prefix="/admin/discovery", tags=["admin-discovery"])


class SourceHealthResponse(BaseModel):
    source_name: str
    status: str
    last_check_at: str | None = None
    last_success_at: str | None = None
    consecutive_failures: int = 0
    avg_response_ms: float = 0.0
    error_rate_24h: float = 0.0
    disabled: bool = False
    last_error: str = ""


class ToggleSourceRequest(BaseModel):
    disabled: bool


class ToggleSourceResponse(BaseModel):
    source_name: str
    disabled: bool


@router.get("/sources/health", response_model=list[SourceHealthResponse])
async def get_source_health(
    _user: User = Depends(get_current_admin_user),
):
    """View per-source availability, freshness, and error rates."""
    repo = DataSourceHealthRepository()
    sources = await repo.get_all_sources()
    return [
        SourceHealthResponse(
            source_name=s.source_name,
            status=s.status,
            last_check_at=s.last_check_at.isoformat() if s.last_check_at else None,
            last_success_at=s.last_success_at.isoformat() if s.last_success_at else None,
            consecutive_failures=s.consecutive_failures,
            avg_response_ms=s.avg_response_ms,
            error_rate_24h=s.error_rate_24h,
            disabled=s.disabled,
            last_error=s.last_error,
        )
        for s in sources
    ]


@router.post("/sources/{source_name}/toggle", response_model=ToggleSourceResponse)
async def toggle_source(
    source_name: str,
    body: ToggleSourceRequest,
    _user: User = Depends(get_current_admin_user),
):
    """Admin toggle to manually enable/disable a data source."""
    repo = DataSourceHealthRepository()
    result = await repo.set_disabled(source_name, body.disabled)
    if result is None:
        raise NotFoundError("DataSource")
    return ToggleSourceResponse(
        source_name=result.source_name,
        disabled=result.disabled,
    )


class CacheAnalyticsResponse(BaseModel):
    total_entries: int = 0
    total_hits: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    avg_cost_per_entry_usd: float = 0.0
    estimated_savings_usd: float = 0.0
    hit_rate: float = 0.0


@router.get("/cache/analytics", response_model=CacheAnalyticsResponse)
async def get_cache_analytics(
    _user: User = Depends(get_current_admin_user),
):
    """JD analysis cache cost analytics — hit rates, savings, token usage."""
    repo = JDCacheRepository()
    stats = await repo.get_analytics()
    return CacheAnalyticsResponse(**stats)
