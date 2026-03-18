"""
Locale routes: profile management, compensation calculators, notice period.

These endpoints provide locale-aware features for users. All require JWT auth.
"""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_locale_service, get_market_config_repository
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.user import (
    LanguageProficiency,
    NoticePeriod,
    User,
    UserLocaleProfile,
    VisaStatus,
)
from src.repositories.market_config_repository import MarketConfigRepository
from src.services.locale_service import LocaleService

logger = structlog.get_logger()

router = APIRouter(prefix="/locale", tags=["locale"])


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class LocaleProfileUpdate(BaseModel):
    """Partial update for user locale profile."""

    primary_market: str | None = None
    target_markets: list[str] | None = None
    nationality: str | None = None
    languages: list[LanguageProficiency] | None = None
    visa_statuses: list[VisaStatus] | None = None
    notice_period: NoticePeriod | None = None
    career_sector: str | None = None
    profile_type: str | None = None
    preferred_response_language: str | None = None


class CTCDecodeRequest(BaseModel):
    """Request to decode an Indian CTC."""

    ctc_annual: float
    city_type: str = "METRO"  # METRO / NON_METRO
    tax_regime: str = "NEW"  # NEW / OLD
    variable_pay_pct: float = 0.0
    joining_bonus: float = 0.0
    retention_bonus: float = 0.0
    esops_value: float = 0.0
    insurance_value: float = 0.0


class SalaryCompareRequest(BaseModel):
    """Request to compare salary across markets."""

    source_amount: float
    source_currency: str = "INR"
    source_region: str = "IN"
    target_region: str = "US"


class NoticePeriodRequest(BaseModel):
    """Request for notice period calculation."""

    action: str  # JOINING_DATE / BUYOUT_COST / DEADLINE_MATCH
    contractual_days: int = 0
    served_days: int = 0
    notice_start_date: str | None = None
    monthly_basic: float = 0
    offer_deadline: str | None = None


# ---------------------------------------------------------------------------
# Locale Profile endpoints
# ---------------------------------------------------------------------------


@router.get("/profile")
async def get_locale_profile(
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Get the current user's locale profile."""
    if not user.locale_profile:
        raise NotFoundError("Locale profile")
    return user.locale_profile.model_dump()


@router.patch("/profile")
async def update_locale_profile(
    body: LocaleProfileUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    market_repo: MarketConfigRepository = Depends(get_market_config_repository),  # noqa: B008
) -> dict:
    """Update the user's locale profile (partial update)."""
    # Validate market codes
    markets_to_check = []
    if body.primary_market:
        markets_to_check.append(body.primary_market)
    if body.target_markets:
        markets_to_check.extend(body.target_markets)

    for code in markets_to_check:
        config = await market_repo.get_by_region(code)
        if not config:
            raise BusinessValidationError(
                detail=f"MarketConfig not found for region code: {code}",
                error_code="MARKET_NOT_FOUND",
            )

    # Build updated profile
    existing = user.locale_profile or UserLocaleProfile()
    update_data = body.model_dump(exclude_none=True)

    for key, value in update_data.items():
        setattr(existing, key, value)

    # Auto-compute earliest joining date
    if existing.notice_period.contractual_days > 0:
        np = existing.notice_period
        start = np.notice_start_date or datetime.now(UTC)
        remaining = max(0, np.contractual_days - np.served_days)
        existing.notice_period.earliest_joining_date = start + timedelta(days=remaining)

    # Set consent timestamp if not already set
    if not existing.consent_granted_at:
        existing.consent_granted_at = datetime.now(UTC)

    await user.set({"locale_profile": existing.model_dump()})
    logger.info("locale_profile_updated", user_id=str(user.id))
    return existing.model_dump()


# ---------------------------------------------------------------------------
# Compensation endpoints
# ---------------------------------------------------------------------------


@router.post("/compensation/ctc-decode")
async def decode_ctc(
    body: CTCDecodeRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    locale_service: LocaleService = Depends(get_locale_service),  # noqa: B008
) -> dict:
    """Decode an Indian CTC into component breakdown with in-hand monthly."""
    if body.ctc_annual <= 0:
        raise BusinessValidationError(
            detail="ctc_annual must be positive",
            error_code="INVALID_CTC",
        )
    if body.city_type not in ("METRO", "NON_METRO"):
        raise BusinessValidationError(
            detail="city_type must be METRO or NON_METRO",
            error_code="INVALID_CITY_TYPE",
        )
    if body.tax_regime not in ("OLD", "NEW"):
        raise BusinessValidationError(
            detail="tax_regime must be OLD or NEW",
            error_code="INVALID_TAX_REGIME",
        )

    result = locale_service.decode_ctc(
        ctc_annual=body.ctc_annual,
        city_type=body.city_type,
        tax_regime=body.tax_regime,
        variable_pay_pct=body.variable_pay_pct,
        joining_bonus=body.joining_bonus,
        retention_bonus=body.retention_bonus,
        esops_value=body.esops_value,
        insurance_value=body.insurance_value,
    )
    return result.model_dump()


@router.post("/compensation/compare")
async def compare_salary(
    body: SalaryCompareRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    locale_service: LocaleService = Depends(get_locale_service),  # noqa: B008
) -> dict:
    """Compare compensation across two markets with PPP adjustment."""
    if body.source_amount <= 0:
        raise BusinessValidationError(
            detail="source_amount must be positive",
            error_code="INVALID_AMOUNT",
        )
    return await locale_service.compare_salary(
        source_amount=body.source_amount,
        source_currency=body.source_currency,
        source_region=body.source_region,
        target_region=body.target_region,
    )


# ---------------------------------------------------------------------------
# Notice Period endpoints
# ---------------------------------------------------------------------------


@router.post("/notice-period/calculate")
async def calculate_notice_period(
    body: NoticePeriodRequest,
    _user: User = Depends(get_current_user),  # noqa: B008
    locale_service: LocaleService = Depends(get_locale_service),  # noqa: B008
) -> dict:
    """Calculate joining date, buyout cost, or deadline feasibility."""
    if body.action not in ("JOINING_DATE", "BUYOUT_COST", "DEADLINE_MATCH"):
        raise BusinessValidationError(
            detail="action must be JOINING_DATE, BUYOUT_COST, or DEADLINE_MATCH",
            error_code="INVALID_ACTION",
        )
    return locale_service.calculate_notice(
        action=body.action,
        contractual_days=body.contractual_days,
        served_days=body.served_days,
        notice_start_date=body.notice_start_date,
        monthly_basic=body.monthly_basic,
        offer_deadline=body.offer_deadline,
    )
