"""
Offer comparison service — side-by-side offer analysis with hidden costs.

Normalizes offers across markets, computes hidden costs, equity scenarios,
and generates a recommended choice via LLM. Pure computation where possible,
LLM only for qualitative recommendation reasoning.
"""

import structlog
from pydantic import BaseModel

from src.agents.offer_analyst import OfferAnalystAgent
from src.db.documents.offer import Offer
from src.services.locale_service import LocaleService

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class HiddenCostAnalysis(BaseModel):
    """Estimated hidden costs for a single offer."""

    commute_cost_monthly: float = 0.0
    relocation_cost_one_time: float = 0.0
    equity_cliff_risk_years: float = 0.0
    clawback_clauses_detected: bool = False
    clawback_details: str = ""
    tax_impact_annual: float = 0.0


class EquityScenario(BaseModel):
    """Equity valuation under different growth assumptions."""

    conservative: float = 0.0
    moderate: float = 0.0
    aggressive: float = 0.0


class NormalizedOffer(BaseModel):
    """Single offer with normalized values for comparison."""

    offer_id: str
    company_name: str
    role_title: str
    in_hand_monthly: float = 0.0
    total_annual_comp: float = 0.0
    benefits_value: float = 0.0
    growth_potential_score: float = 0.0
    locale_market: str = ""
    currency: str = "INR"
    components: list[dict] = []
    ppp_adjusted_annual: float | None = None
    hidden_costs: HiddenCostAnalysis = HiddenCostAnalysis()
    equity_scenarios: EquityScenario | None = None


class ComparisonResult(BaseModel):
    """Full comparison result across multiple offers."""

    offers: list[NormalizedOffer]
    cross_market: bool = False
    recommended_choice: str = ""
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Hidden cost analysis
# ---------------------------------------------------------------------------


def _detect_clawback(raw_text: str) -> tuple[bool, str]:
    """Scan offer text for clawback/repayment terms."""
    keywords = [
        "clawback", "repayment", "repay", "return the bonus",
        "payback", "recovery", "reimburse", "forfeiture",
    ]
    raw_lower = raw_text.lower()
    found = [kw for kw in keywords if kw in raw_lower]
    if found:
        return True, f"Detected terms: {', '.join(found)}"
    return False, ""


def _estimate_equity_cliff(components: list) -> float:
    """Estimate years before first vest from component data."""
    for comp in components:
        name = comp.name.lower() if hasattr(comp, "name") else ""
        if any(kw in name for kw in ("esop", "rsu", "stock", "equity")):
            # Standard cliff is 1 year; if value exists, assume cliff
            return 1.0
    return 0.0


def _compute_hidden_costs(offer: Offer) -> HiddenCostAnalysis:
    """Compute hidden cost analysis for a single offer."""
    clawback_detected, clawback_details = _detect_clawback(offer.raw_text)
    equity_cliff = _estimate_equity_cliff(offer.components)

    return HiddenCostAnalysis(
        commute_cost_monthly=0.0,
        relocation_cost_one_time=0.0,
        equity_cliff_risk_years=equity_cliff,
        clawback_clauses_detected=clawback_detected,
        clawback_details=clawback_details,
        tax_impact_annual=0.0,
    )


# ---------------------------------------------------------------------------
# Equity scenarios
# ---------------------------------------------------------------------------


def _compute_equity_scenarios(components: list) -> EquityScenario | None:
    """Compute 3 equity valuation scenarios if equity components exist."""
    equity_value = 0.0
    for comp in components:
        name = comp.name.lower() if hasattr(comp, "name") else ""
        if any(kw in name for kw in ("esop", "rsu", "stock", "equity")):
            equity_value += comp.value if hasattr(comp, "value") else 0.0

    if equity_value <= 0:
        return None

    return EquityScenario(
        conservative=round(equity_value * 0.5, 2),
        moderate=round(equity_value * 1.0, 2),
        aggressive=round(equity_value * 2.0, 2),
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_offer(offer: Offer) -> NormalizedOffer:
    """Normalize a single offer into comparison-ready format."""
    total = offer.total_comp_annual
    in_hand_monthly = 0.0
    benefits_value = 0.0
    growth_score = 0.0
    comp_dicts = []

    for comp in offer.components:
        comp_dict = {
            "name": comp.name,
            "value": comp.value,
            "currency": comp.currency,
            "frequency": comp.frequency,
            "is_guaranteed": comp.is_guaranteed,
        }
        comp_dicts.append(comp_dict)

        name_lower = comp.name.lower()
        if name_lower == "in-hand monthly":
            in_hand_monthly = comp.value
        elif any(kw in name_lower for kw in ("insurance", "benefit", "pf", "gratuity")):
            benefits_value += comp.value

        # Growth potential from equity/stock components
        if any(kw in name_lower for kw in ("esop", "rsu", "stock", "equity")):
            growth_score += comp.value

    # Estimate in-hand monthly if not explicitly provided
    if in_hand_monthly == 0.0 and total > 0:
        in_hand_monthly = round(total / 12, 2)

    # Growth score as percentage of total comp
    growth_potential = round((growth_score / total * 100) if total > 0 else 0.0, 1)

    currency = offer.components[0].currency if offer.components else "INR"

    return NormalizedOffer(
        offer_id=str(offer.id),
        company_name=offer.company_name,
        role_title=offer.role_title,
        in_hand_monthly=in_hand_monthly,
        total_annual_comp=total,
        benefits_value=benefits_value,
        growth_potential_score=growth_potential,
        locale_market=offer.locale_market,
        currency=currency,
        components=comp_dicts,
        hidden_costs=_compute_hidden_costs(offer),
        equity_scenarios=_compute_equity_scenarios(offer.components),
    )


# ---------------------------------------------------------------------------
# PPP adjustment
# ---------------------------------------------------------------------------


async def _apply_ppp(
    offers: list[NormalizedOffer],
    locale_service: LocaleService,
) -> bool:
    """Apply PPP adjustments if offers span multiple markets. Returns cross_market flag."""
    markets = {o.locale_market for o in offers if o.locale_market}
    if len(markets) <= 1:
        return False

    # Use the first offer's market as the reference for PPP conversion
    reference = offers[0]
    for offer in offers[1:]:
        if offer.locale_market != reference.locale_market:
            try:
                result = await locale_service.compare_salary(
                    source_amount=offer.total_annual_comp,
                    source_currency=offer.currency,
                    source_region=offer.locale_market,
                    target_region=reference.locale_market,
                )
                if "error" not in result:
                    ppp_data = result.get("ppp_adjusted", {})
                    offer.ppp_adjusted_annual = ppp_data.get("equivalent")
            except Exception:
                logger.warning(
                    "ppp_conversion_failed",
                    source=offer.locale_market,
                    target=reference.locale_market,
                )
    return True


# ---------------------------------------------------------------------------
# LLM recommendation
# ---------------------------------------------------------------------------


async def _generate_recommendation(
    offers: list[NormalizedOffer],
    user_id: str,
) -> tuple[str, str]:
    """Use OfferAnalystAgent to generate recommended choice and reasoning."""
    summary_lines = []
    for o in offers:
        line = (
            f"- {o.company_name} ({o.role_title}): "
            f"Total annual = {o.total_annual_comp} {o.currency}, "
            f"In-hand monthly = {o.in_hand_monthly}, "
            f"Benefits = {o.benefits_value}, "
            f"Growth score = {o.growth_potential_score}%"
        )
        if o.hidden_costs.clawback_clauses_detected:
            line += f", CLAWBACK: {o.hidden_costs.clawback_details}"
        if o.equity_scenarios:
            line += (
                f", Equity scenarios: "
                f"conservative={o.equity_scenarios.conservative}, "
                f"moderate={o.equity_scenarios.moderate}, "
                f"aggressive={o.equity_scenarios.aggressive}"
            )
        if o.ppp_adjusted_annual is not None:
            line += f", PPP-adjusted = {o.ppp_adjusted_annual}"
        summary_lines.append(line)

    comparison_text = (
        "Compare these offers and recommend which one to accept. "
        "Consider total comp, in-hand monthly, benefits, growth potential, "
        "hidden costs, and equity scenarios. Provide a clear recommendation "
        "and detailed reasoning.\n\n"
        + "\n".join(summary_lines)
    )

    agent = OfferAnalystAgent()
    state = {
        "offer_text": comparison_text,
        "company_name": "Multiple",
        "role_title": "Comparison",
        "locale_market": "",
    }
    config = {"configurable": {"user_id": user_id}}

    try:
        result = await agent(state, config)
        suggestions = result.get("suggestions", [])
        if suggestions:
            recommended = suggestions[0] if len(suggestions) > 0 else ""
            reasoning = " ".join(suggestions[1:]) if len(suggestions) > 1 else ""
            return recommended, reasoning
    except Exception:
        logger.warning("offer_comparison_recommendation_failed")

    return "", ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def compare_offers(
    offers: list[Offer],
    locale_service: LocaleService,
    user_id: str,
) -> ComparisonResult:
    """Compare multiple offers side-by-side with hidden costs and recommendation."""
    normalized = [_normalize_offer(o) for o in offers]

    cross_market = await _apply_ppp(normalized, locale_service)

    recommended, reasoning = await _generate_recommendation(normalized, user_id)

    return ComparisonResult(
        offers=normalized,
        cross_market=cross_market,
        recommended_choice=recommended,
        reasoning=reasoning,
    )
