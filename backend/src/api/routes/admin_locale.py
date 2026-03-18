"""
Admin routes for MarketConfig CRUD.

These endpoints are for managing market configurations (creating new markets,
updating existing ones, deleting markets). In production, these would be
protected by admin-role authorization. For now, they require JWT auth.

Endpoints
---------
    GET    /admin/markets           List all market configs
    GET    /admin/markets/{code}    Get a specific market config
    POST   /admin/markets           Create a new market config
    PUT    /admin/markets/{code}    Update (replace) a market config
    DELETE /admin/markets/{code}    Delete a market config
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_market_config_repository
from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.market_config import (
    CompensationStructure,
    CulturalContext,
    HiringProcess,
    InfrastructureContext,
    JobPlatformConfig,
    LegalProvisions,
    MarketConfig,
    ResumeConventions,
)
from src.db.documents.user import User
from src.repositories.market_config_repository import MarketConfigRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/markets", tags=["admin"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MarketConfigCreate(BaseModel):
    """Request body to create a MarketConfig."""

    region_code: str
    region_name: str = ""
    compensation_structure: CompensationStructure = CompensationStructure()
    hiring_process: HiringProcess = HiringProcess()
    resume_conventions: ResumeConventions = ResumeConventions()
    job_platforms: list[JobPlatformConfig] = []
    legal: LegalProvisions = LegalProvisions()
    cultural: CulturalContext = CulturalContext()
    infrastructure: InfrastructureContext = InfrastructureContext()


class MarketConfigUpdate(BaseModel):
    """Request body to update a MarketConfig (full replace)."""

    region_name: str | None = None
    compensation_structure: CompensationStructure | None = None
    hiring_process: HiringProcess | None = None
    resume_conventions: ResumeConventions | None = None
    job_platforms: list[JobPlatformConfig] | None = None
    legal: LegalProvisions | None = None
    cultural: CulturalContext | None = None
    infrastructure: InfrastructureContext | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_markets(
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> list[dict]:
    """List all market configurations."""
    configs = await market_repo.find_many()
    return [c.model_dump() for c in configs]


@router.get("/{region_code}")
async def get_market(
    region_code: str,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Get a specific market configuration by region code."""
    config = await market_repo.get_by_region(region_code.upper())
    if not config:
        raise NotFoundError(f"MarketConfig for region '{region_code}'")
    return config.model_dump()


@router.post("", status_code=201)
async def create_market(
    body: MarketConfigCreate,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Create a new market configuration."""
    code = body.region_code.upper()
    if len(code) != 2:
        raise BusinessValidationError(
            detail="region_code must be a 2-letter ISO 3166-1 alpha-2 code",
            error_code="INVALID_REGION_CODE",
        )

    existing = await market_repo.get_by_region(code)
    if existing:
        raise ConflictError(f"MarketConfig for region '{code}' already exists")

    config = MarketConfig(
        region_code=code,
        region_name=body.region_name,
        compensation_structure=body.compensation_structure,
        hiring_process=body.hiring_process,
        resume_conventions=body.resume_conventions,
        job_platforms=body.job_platforms,
        legal=body.legal,
        cultural=body.cultural,
        infrastructure=body.infrastructure,
    )
    await config.insert()
    logger.info("market_config_created", region_code=code)
    return config.model_dump()


@router.put("/{region_code}")
async def update_market(
    region_code: str,
    body: MarketConfigUpdate,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Update (partial) a market configuration. Increments version."""
    code = region_code.upper()
    config = await market_repo.get_by_region(code)
    if not config:
        raise NotFoundError(f"MarketConfig for region '{code}'")

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    config.version += 1
    await config.save()
    logger.info("market_config_updated", region_code=code, version=config.version)
    return config.model_dump()


@router.delete("/{region_code}", status_code=204)
async def delete_market(
    region_code: str,
    _user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> None:
    """Delete a market configuration."""
    code = region_code.upper()
    config = await market_repo.get_by_region(code)
    if not config:
        raise NotFoundError(f"MarketConfig for region '{code}'")

    await config.delete()
    logger.info("market_config_deleted", region_code=code)
