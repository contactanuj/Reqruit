"""
Market positioning service — computes where an offer sits relative to market rates.

Pure computation: percentile interpolation against salary benchmark data.
No LLM calls needed.
"""

import re

import structlog

from src.db.documents.offer import Offer
from src.db.documents.salary_benchmark import SalaryBenchmark
from src.repositories.salary_benchmark_repository import SalaryBenchmarkRepository

logger = structlog.get_logger()


class MarketPositionResult:
    """Result of market position computation."""

    def __init__(
        self,
        market_percentile: float = 0.0,
        percentile_label: str = "",
        salary_range: dict | None = None,
        confidence_level: str = "LOW",
        data_source: str = "",
        last_updated: str = "",
        approximate_match: bool = False,
        approximate_match_explanation: str | None = None,
        data_available: bool = False,
    ):
        self.market_percentile = market_percentile
        self.percentile_label = percentile_label
        self.salary_range = salary_range or {}
        self.confidence_level = confidence_level
        self.data_source = data_source
        self.last_updated = last_updated
        self.approximate_match = approximate_match
        self.approximate_match_explanation = approximate_match_explanation
        self.data_available = data_available


def _normalize_role_family(role: str) -> str:
    """Extract broad role family from specific title.

    E.g., "Software Engineer II" -> "Software Engineer",
          "Senior SDE" -> "SDE", "Staff Backend Engineer" -> "Backend Engineer"
    """
    cleaned = re.sub(
        r"\b(Senior|Staff|Principal|Lead|Junior|Jr\.?|Sr\.?|I{1,3}|IV|V)\b",
        "",
        role,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove trailing dashes/numbers like "SDE-2" -> "SDE"
    cleaned = re.sub(r"[-\s]+\d+$", "", cleaned).strip()
    return cleaned or role


def _compute_percentile(value: float, benchmark: SalaryBenchmark) -> float:
    """Linearly interpolate percentile from benchmark p25/p50/p75/p90."""
    if value <= benchmark.p25:
        # Below p25: extrapolate down, floor at 0
        if benchmark.p25 > 0:
            return max(0.0, 25.0 * value / benchmark.p25)
        return 0.0

    breakpoints = [
        (benchmark.p25, 25.0),
        (benchmark.p50, 50.0),
        (benchmark.p75, 75.0),
        (benchmark.p90, 90.0),
    ]

    for i in range(len(breakpoints) - 1):
        low_val, low_pct = breakpoints[i]
        high_val, high_pct = breakpoints[i + 1]
        if low_val <= value <= high_val:
            if high_val == low_val:
                return low_pct
            ratio = (value - low_val) / (high_val - low_val)
            return low_pct + ratio * (high_pct - low_pct)

    # Above p90: extrapolate up, cap at 99
    if value > benchmark.p90 and benchmark.p90 > benchmark.p75:
        extra = (value - benchmark.p90) / (benchmark.p90 - benchmark.p75) * 10
        return min(99.0, 90.0 + extra)

    return 90.0


def _confidence_level(sample_size: int) -> str:
    """Determine confidence from sample size."""
    if sample_size >= 50:
        return "HIGH"
    if sample_size >= 10:
        return "MEDIUM"
    return "LOW"


def _percentile_label(percentile: float, role: str, region: str) -> str:
    """Generate human-readable label."""
    return f"Your offer is at p{int(round(percentile))} for {role} in {region}"


async def compute_market_position(
    offer: Offer,
    benchmark_repo: SalaryBenchmarkRepository,
) -> MarketPositionResult:
    """Compute where an offer falls relative to market rates."""
    role = offer.role_title
    region = offer.locale_market or "IN"
    total_comp = offer.total_comp_annual

    if total_comp <= 0:
        return MarketPositionResult(data_available=False)

    # Try exact role + region match
    benchmark = await benchmark_repo.find_by_role_and_region(role, region)
    approximate = False
    approx_explanation = None

    # Fallback to role family
    if benchmark is None:
        family = _normalize_role_family(role)
        benchmark = await benchmark_repo.find_by_family_and_region(family, region)
        if benchmark is not None:
            approximate = True
            approx_explanation = (
                f"No exact data for '{role}'. "
                f"Using '{family}' role family benchmarks instead."
            )

    if benchmark is None:
        logger.info("no_benchmark_found", role=role, region=region)
        return MarketPositionResult(data_available=False)

    percentile = _compute_percentile(total_comp, benchmark)
    confidence = _confidence_level(benchmark.sample_size)
    label = _percentile_label(percentile, role, region)
    last_updated = ""
    if benchmark.updated_at:
        last_updated = benchmark.updated_at.isoformat()
    elif benchmark.created_at:
        last_updated = benchmark.created_at.isoformat()

    return MarketPositionResult(
        market_percentile=round(percentile, 1),
        percentile_label=label,
        salary_range={
            "p25": benchmark.p25,
            "p50": benchmark.p50,
            "p75": benchmark.p75,
            "p90": benchmark.p90,
            "currency": benchmark.currency_code,
        },
        confidence_level=confidence,
        data_source=benchmark.source,
        last_updated=last_updated,
        approximate_match=approximate,
        approximate_match_explanation=approx_explanation,
        data_available=True,
    )
