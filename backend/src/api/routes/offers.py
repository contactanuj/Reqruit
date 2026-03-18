"""
Offer routes: parse and analyze compensation offers.

Endpoints for submitting offer text, getting structured breakdowns,
and comparing offers. All require JWT auth.
"""

import time
from datetime import datetime, timezone

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from src.agents.offer_analyst import OfferAnalystAgent
from src.db.documents.offer import NegotiationOutcome
from src.api.dependencies import (
    get_current_user,
    get_locale_service,
    get_offer_repository,
    get_salary_benchmark_repository,
)
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.offer import Offer, OfferComponent
from src.db.documents.user import User
from src.repositories.offer_repository import OfferRepository
from src.repositories.salary_benchmark_repository import SalaryBenchmarkRepository
from src.services.locale_service import LocaleService
from src.services.market_positioning import compute_market_position
from src.services.offer_comparison import (
    ComparisonResult,
    compare_offers,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/offers", tags=["offers"])


# ---------------------------------------------------------------------------
# Inline Pydantic schemas
# ---------------------------------------------------------------------------


class OfferAnalyzeRequest(BaseModel):
    offer_text: str
    company_name: str
    role_title: str
    application_id: PydanticObjectId | None = None


class OfferComponentResponse(BaseModel):
    name: str
    value: float
    currency: str = "INR"
    frequency: str = "annual"
    is_guaranteed: bool = True
    confidence: str = "high"
    pct_of_total: float = 0.0


class OfferAnalyzeResponse(BaseModel):
    offer_id: str
    company_name: str
    role_title: str
    components: list[OfferComponentResponse]
    total_comp_annual: float
    missing_fields: list[str]
    suggestions: list[str]
    locale_market: str


class MarketPositionResponse(BaseModel):
    market_percentile: float
    percentile_label: str
    salary_range: dict
    confidence_level: str
    data_source: str
    last_updated: str
    approximate_match: bool
    approximate_match_explanation: str | None = None
    data_available: bool


# ---------------------------------------------------------------------------
# POST /offers/analyze
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=OfferAnalyzeResponse, status_code=201)
async def analyze_offer(
    body: OfferAnalyzeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    locale_service: LocaleService = Depends(get_locale_service),  # noqa: B008
) -> OfferAnalyzeResponse:
    """Parse an offer letter into structured compensation components."""
    start_time = time.monotonic()

    locale_market = getattr(request.state, "primary_market", None) or ""

    # Invoke OfferAnalystAgent
    agent = OfferAnalystAgent()
    state = {
        "offer_text": body.offer_text,
        "company_name": body.company_name,
        "role_title": body.role_title,
        "locale_market": locale_market,
    }
    config = {"configurable": {"user_id": str(current_user.id)}}
    result = await agent(state, config)

    components_raw = result.get("components", [])
    total_comp = result.get("total_comp_annual", 0.0)
    missing_fields = result.get("missing_fields", [])
    suggestions = result.get("suggestions", [])

    # India CTC decode integration: if locale is IN and CTC detected,
    # enrich components with LocaleService.decode_ctc()
    if locale_market == "IN" and total_comp > 0:
        try:
            ctc_result = locale_service.decode_ctc(ctc_annual=total_comp)
            ctc_components = []
            for comp in ctc_result.components:
                ctc_components.append({
                    "name": comp.name,
                    "value": comp.value,
                    "currency": "INR",
                    "frequency": "annual",
                    "is_guaranteed": comp.name.lower() not in (
                        "variable pay", "esops", "joining bonus", "retention bonus"
                    ),
                    "confidence": "high",
                })
            # Replace agent components with CTC-decoded ones if available
            if ctc_components:
                components_raw = ctc_components
                total_comp = ctc_result.ctc_annual
                # Add in_hand_monthly as a special component
                components_raw.append({
                    "name": "In-Hand Monthly",
                    "value": ctc_result.in_hand_monthly,
                    "currency": "INR",
                    "frequency": "monthly",
                    "is_guaranteed": True,
                    "confidence": "high",
                })
        except Exception:
            logger.warning("ctc_decode_failed", locale=locale_market)

    # Compute pct_of_total for each component
    offer_components = []
    for comp_data in components_raw:
        value = comp_data.get("value", 0.0)
        # Annualize monthly values for percentage calculation
        annualized = value * 12 if comp_data.get("frequency") == "monthly" else value
        pct = (annualized / total_comp * 100) if total_comp > 0 else 0.0
        offer_components.append(
            OfferComponent(
                name=comp_data.get("name", "Unknown"),
                value=value,
                currency=comp_data.get("currency", "INR"),
                frequency=comp_data.get("frequency", "annual"),
                is_guaranteed=comp_data.get("is_guaranteed", True),
                confidence=comp_data.get("confidence", "high"),
                pct_of_total=round(pct, 2),
            )
        )

    # Persist Offer document
    offer = Offer(
        user_id=current_user.id,
        application_id=body.application_id,
        company_name=body.company_name,
        role_title=body.role_title,
        components=offer_components,
        total_comp_annual=total_comp,
        locale_market=locale_market,
        raw_text=body.offer_text,
        missing_fields=missing_fields,
        suggestions=suggestions,
    )
    offer = await offer_repo.create(offer)

    duration_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "offer_analysis_completed",
        offer_id=str(offer.id),
        company=body.company_name,
        locale=locale_market,
        components_count=len(offer_components),
        duration_ms=round(duration_ms, 1),
    )

    return OfferAnalyzeResponse(
        offer_id=str(offer.id),
        company_name=offer.company_name,
        role_title=offer.role_title,
        components=[
            OfferComponentResponse(
                name=c.name,
                value=c.value,
                currency=c.currency,
                frequency=c.frequency,
                is_guaranteed=c.is_guaranteed,
                confidence=c.confidence,
                pct_of_total=c.pct_of_total,
            )
            for c in offer_components
        ],
        total_comp_annual=total_comp,
        missing_fields=missing_fields,
        suggestions=suggestions,
        locale_market=locale_market,
    )


# ---------------------------------------------------------------------------
# GET /offers/{offer_id}/market-position
# ---------------------------------------------------------------------------


@router.get(
    "/{offer_id}/market-position",
    response_model=MarketPositionResponse,
)
async def get_market_position(
    offer_id: PydanticObjectId,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    benchmark_repo: SalaryBenchmarkRepository = Depends(  # noqa: B008
        get_salary_benchmark_repository
    ),
) -> MarketPositionResponse:
    """Return market percentile positioning for a specific offer."""
    offer = await offer_repo.get_by_user_and_id(current_user.id, offer_id)
    if offer is None:
        raise NotFoundError(f"Offer {offer_id} not found")

    result = await compute_market_position(offer, benchmark_repo)

    return MarketPositionResponse(
        market_percentile=result.market_percentile,
        percentile_label=result.percentile_label,
        salary_range=result.salary_range,
        confidence_level=result.confidence_level,
        data_source=result.data_source,
        last_updated=result.last_updated,
        approximate_match=result.approximate_match,
        approximate_match_explanation=result.approximate_match_explanation,
        data_available=result.data_available,
    )


# ---------------------------------------------------------------------------
# POST /offers/compare
# ---------------------------------------------------------------------------


class OfferCompareRequest(BaseModel):
    offer_ids: list[PydanticObjectId]


class HiddenCostResponse(BaseModel):
    commute_cost_monthly: float = 0.0
    relocation_cost_one_time: float = 0.0
    equity_cliff_risk_years: float = 0.0
    clawback_clauses_detected: bool = False
    clawback_details: str = ""
    tax_impact_annual: float = 0.0


class EquityScenarioResponse(BaseModel):
    conservative: float = 0.0
    moderate: float = 0.0
    aggressive: float = 0.0


class NormalizedOfferResponse(BaseModel):
    offer_id: str
    company_name: str
    role_title: str
    in_hand_monthly: float
    total_annual_comp: float
    benefits_value: float
    growth_potential_score: float
    locale_market: str
    currency: str
    components: list[dict]
    ppp_adjusted_annual: float | None = None
    hidden_costs: HiddenCostResponse
    equity_scenarios: EquityScenarioResponse | None = None


class OfferCompareResponse(BaseModel):
    offers: list[NormalizedOfferResponse]
    cross_market: bool
    recommended_choice: str
    reasoning: str


@router.post("/compare", response_model=OfferCompareResponse)
async def compare_offers_endpoint(
    body: OfferCompareRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
    locale_service: LocaleService = Depends(get_locale_service),  # noqa: B008
) -> OfferCompareResponse:
    """Compare multiple offers side-by-side with hidden costs and recommendation."""
    if len(body.offer_ids) < 2:
        raise BusinessValidationError(
            detail="At least 2 offers are required for comparison",
            error_code="INSUFFICIENT_OFFERS_FOR_COMPARISON",
        )

    offers = await offer_repo.compare_offers(current_user.id, body.offer_ids)

    if len(offers) != len(body.offer_ids):
        raise NotFoundError("One or more offers not found")

    result = await compare_offers(
        offers=offers,
        locale_service=locale_service,
        user_id=str(current_user.id),
    )

    return OfferCompareResponse(
        offers=[
            NormalizedOfferResponse(
                offer_id=o.offer_id,
                company_name=o.company_name,
                role_title=o.role_title,
                in_hand_monthly=o.in_hand_monthly,
                total_annual_comp=o.total_annual_comp,
                benefits_value=o.benefits_value,
                growth_potential_score=o.growth_potential_score,
                locale_market=o.locale_market,
                currency=o.currency,
                components=o.components,
                ppp_adjusted_annual=o.ppp_adjusted_annual,
                hidden_costs=HiddenCostResponse(
                    commute_cost_monthly=o.hidden_costs.commute_cost_monthly,
                    relocation_cost_one_time=o.hidden_costs.relocation_cost_one_time,
                    equity_cliff_risk_years=o.hidden_costs.equity_cliff_risk_years,
                    clawback_clauses_detected=o.hidden_costs.clawback_clauses_detected,
                    clawback_details=o.hidden_costs.clawback_details,
                    tax_impact_annual=o.hidden_costs.tax_impact_annual,
                ),
                equity_scenarios=(
                    EquityScenarioResponse(
                        conservative=o.equity_scenarios.conservative,
                        moderate=o.equity_scenarios.moderate,
                        aggressive=o.equity_scenarios.aggressive,
                    )
                    if o.equity_scenarios
                    else None
                ),
            )
            for o in result.offers
        ],
        cross_market=result.cross_market,
        recommended_choice=result.recommended_choice,
        reasoning=result.reasoning,
    )


# ---------------------------------------------------------------------------
# POST /offers/{offer_id}/outcome
# ---------------------------------------------------------------------------


class RecordOutcomeRequest(BaseModel):
    initial_offer_total: float
    final_offer_total: float
    negotiation_strategy_used: str
    outcome_notes: str = ""
    role_family: str = ""
    company_stage: str = ""
    region: str = ""


class RecordOutcomeResponse(BaseModel):
    offer_id: str
    company_name: str
    delta_absolute: float
    delta_percentage: float
    strategy_used: str


@router.post("/{offer_id}/outcome", response_model=RecordOutcomeResponse)
async def record_outcome(
    offer_id: PydanticObjectId,
    body: RecordOutcomeRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
) -> RecordOutcomeResponse:
    """Record the final negotiation outcome on an offer."""
    delta_absolute = body.final_offer_total - body.initial_offer_total
    delta_percentage = (
        (delta_absolute / body.initial_offer_total) * 100
        if body.initial_offer_total != 0
        else 0.0
    )

    outcome = NegotiationOutcome(
        initial_offer_total=body.initial_offer_total,
        final_offer_total=body.final_offer_total,
        delta_absolute=delta_absolute,
        delta_percentage=round(delta_percentage, 2),
        strategy_used=body.negotiation_strategy_used,
        outcome_notes=body.outcome_notes,
        recorded_at=datetime.now(tz=timezone.utc),
    )

    offer = await offer_repo.record_outcome(
        offer_id=offer_id,
        user_id=current_user.id,
        outcome=outcome,
        role_family=body.role_family,
        company_stage=body.company_stage,
        region=body.region,
    )
    if offer is None:
        raise NotFoundError(f"Offer {offer_id} not found")

    logger.info(
        "negotiation_outcome_recorded",
        offer_id=str(offer_id),
        delta_pct=delta_percentage,
        strategy=body.negotiation_strategy_used,
    )

    return RecordOutcomeResponse(
        offer_id=str(offer.id),
        company_name=offer.company_name,
        delta_absolute=delta_absolute,
        delta_percentage=round(delta_percentage, 2),
        strategy_used=body.negotiation_strategy_used,
    )


# ---------------------------------------------------------------------------
# GET /offers/negotiation-history
# ---------------------------------------------------------------------------


class NegotiationOutcomeItem(BaseModel):
    offer_id: str
    company_name: str
    role_title: str
    initial_offer_total: float
    final_offer_total: float
    delta_absolute: float
    delta_percentage: float
    strategy_used: str
    recorded_at: str


class ImprovementTrend(BaseModel):
    direction: str  # improving, declining, stable
    avg_recent_delta_pct: float


class NegotiationHistoryResponse(BaseModel):
    offers: list[NegotiationOutcomeItem]
    strategy_stats: dict
    improvement_trend: ImprovementTrend


@router.get(
    "/negotiation-history",
    response_model=NegotiationHistoryResponse,
)
async def get_negotiation_history(
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
) -> NegotiationHistoryResponse:
    """Return the user's negotiation history with strategy stats and trend."""
    offers = await offer_repo.get_negotiation_history(current_user.id)
    strategy_stats = await offer_repo.get_strategy_success_rates(current_user.id)

    # Build outcome items
    items = []
    for o in offers:
        outcome = o.negotiation_outcome
        if outcome is None:
            continue
        items.append(NegotiationOutcomeItem(
            offer_id=str(o.id),
            company_name=o.company_name,
            role_title=o.role_title,
            initial_offer_total=outcome.initial_offer_total,
            final_offer_total=outcome.final_offer_total,
            delta_absolute=outcome.delta_absolute,
            delta_percentage=outcome.delta_percentage,
            strategy_used=outcome.strategy_used,
            recorded_at=outcome.recorded_at.isoformat(),
        ))

    # Compute improvement trend: compare recent 3 vs oldest 3
    deltas = [i.delta_percentage for i in items]
    if len(deltas) >= 6:
        recent_avg = sum(deltas[:3]) / 3  # items sorted newest first
        oldest_avg = sum(deltas[-3:]) / 3
        if recent_avg > oldest_avg + 1.0:
            direction = "improving"
        elif recent_avg < oldest_avg - 1.0:
            direction = "declining"
        else:
            direction = "stable"
        avg_recent = round(recent_avg, 2)
    elif deltas:
        avg_recent = round(sum(deltas) / len(deltas), 2)
        direction = "stable"
    else:
        avg_recent = 0.0
        direction = "stable"

    logger.info(
        "negotiation_history_retrieved",
        user_id=str(current_user.id),
        outcome_count=len(items),
    )

    return NegotiationHistoryResponse(
        offers=items,
        strategy_stats=strategy_stats,
        improvement_trend=ImprovementTrend(
            direction=direction,
            avg_recent_delta_pct=avg_recent,
        ),
    )


# ---------------------------------------------------------------------------
# GET /offers/benchmarks
# ---------------------------------------------------------------------------


class BenchmarkResponse(BaseModel):
    data_available: bool
    message: str = ""
    cohort_size: int = 0
    benchmarks: dict = {}
    confidence_level: str = ""


@router.get("/benchmarks", response_model=BenchmarkResponse)
async def get_benchmarks(
    role_family: str = Query(...),
    region: str = Query(...),
    company_stage: str | None = Query(None),
    current_user: User = Depends(get_current_user),  # noqa: B008
    offer_repo: OfferRepository = Depends(get_offer_repository),  # noqa: B008
) -> BenchmarkResponse:
    """Return anonymized negotiation benchmarks (min cohort 10)."""
    result = await offer_repo.get_anonymized_benchmarks(
        role_family=role_family,
        region=region,
        company_stage=company_stage,
    )

    cohort_size = result.get("cohort_size", 0)

    if cohort_size < 10:
        logger.info(
            "benchmark_query_insufficient_data",
            role_family=role_family,
            region=region,
            cohort_size=cohort_size,
        )
        return BenchmarkResponse(
            data_available=False,
            message="Insufficient data for reliable benchmark",
            cohort_size=cohort_size,
        )

    # Compute confidence level
    if cohort_size >= 100:
        confidence = "high"
    elif cohort_size >= 30:
        confidence = "medium"
    else:
        confidence = "low"

    # Compute strategy success rates from strategies list
    strategies = result.get("strategies", [])
    strategy_counts: dict[str, dict] = {}
    deltas = result.get("deltas", [])
    for i, strategy in enumerate(strategies):
        if strategy not in strategy_counts:
            strategy_counts[strategy] = {"count": 0, "successes": 0}
        strategy_counts[strategy]["count"] += 1
        if i < len(deltas) and deltas[i] > 0:
            strategy_counts[strategy]["successes"] += 1

    success_by_strategy = {}
    for strategy, data in strategy_counts.items():
        success_by_strategy[strategy] = round(
            data["successes"] / data["count"], 2
        ) if data["count"] else 0.0

    # Compute median delta
    sorted_deltas = sorted(deltas) if deltas else []
    if sorted_deltas:
        mid = len(sorted_deltas) // 2
        median = (
            sorted_deltas[mid]
            if len(sorted_deltas) % 2
            else (sorted_deltas[mid - 1] + sorted_deltas[mid]) / 2
        )
    else:
        median = 0.0

    logger.info(
        "benchmark_query_served",
        role_family=role_family,
        region=region,
        cohort_size=cohort_size,
        confidence=confidence,
    )

    return BenchmarkResponse(
        data_available=True,
        cohort_size=cohort_size,
        confidence_level=confidence,
        benchmarks={
            "avg_delta_pct": round(result.get("avg_delta_pct", 0.0), 2),
            "median_delta_pct": round(median, 2),
            "success_rate_by_strategy": success_by_strategy,
        },
    )
