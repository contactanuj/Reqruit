"""
Locale service — business logic for market-aware features.

Provides pure-Python calculators (CTC decode, salary comparison, notice
period) and cached MarketConfig access. The LLM agents in this module's
domain (CompensationAnalystAgent, LocaleAdvisorAgent) add qualitative
narrative on top of the quantitative calculations here.

Design decisions
----------------
Why pure Python for calculators (not LLM calls):
    CTC decomposition, PPP adjustment, and notice period math are
    deterministic. Using an LLM would add latency, cost, and
    non-determinism for calculations that have exact right answers.

Why in-memory cache for MarketConfig:
    MarketConfig changes rarely (admin-only updates). An in-memory dict
    with TTL avoids hitting MongoDB on every request. Cache invalidation
    is triggered explicitly by admin update/delete endpoints.
"""

import time
from datetime import UTC, datetime, timedelta

import structlog
from pydantic import BaseModel

from src.db.documents.market_config import MarketConfig
from src.repositories.market_config_repository import MarketConfigRepository
from src.services.currency_service import CurrencyService

logger = structlog.get_logger()

_DEFAULT_CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class CompensationComponent(BaseModel):
    """A single line item in the CTC breakdown."""

    name: str
    value: float
    pct_of_ctc: float


class IndianCompensation(BaseModel):
    """Full CTC-to-in-hand breakdown."""

    ctc_annual: float
    basic: float
    hra: float
    special_allowance: float
    employer_pf: float
    employee_pf: float
    gratuity: float
    variable_pay: float = 0.0
    variable_payout_pct: float = 100.0
    joining_bonus: float = 0.0
    retention_bonus: float = 0.0
    esops_value: float = 0.0
    insurance_value: float = 0.0
    in_hand_monthly: float = 0.0
    tax_annual_estimated: float = 0.0
    tax_regime: str = "NEW"
    city_type: str = "METRO"
    components: list[CompensationComponent] = []


# ---------------------------------------------------------------------------
# Tax slabs (data-driven for easy updates)
# ---------------------------------------------------------------------------

# New Regime (FY 2024-25 onwards, updated per Finance Act)
_NEW_REGIME_SLABS: list[tuple[float, float, float]] = [
    # (lower_bound, upper_bound, rate)
    (0, 300_000, 0.0),
    (300_000, 700_000, 0.05),
    (700_000, 1_000_000, 0.10),
    (1_000_000, 1_200_000, 0.15),
    (1_200_000, 1_500_000, 0.20),
    (1_500_000, float("inf"), 0.30),
]

# Old Regime (simplified — without deductions for now)
_OLD_REGIME_SLABS: list[tuple[float, float, float]] = [
    (0, 250_000, 0.0),
    (250_000, 500_000, 0.05),
    (500_000, 1_000_000, 0.20),
    (1_000_000, float("inf"), 0.30),
]

# Standard deduction under new regime
_NEW_REGIME_STANDARD_DEDUCTION = 75_000
# Standard deduction under old regime
_OLD_REGIME_STANDARD_DEDUCTION = 50_000


def _compute_tax(taxable_income: float, regime: str) -> float:
    """Compute income tax for a given taxable income and regime."""
    slabs = _NEW_REGIME_SLABS if regime == "NEW" else _OLD_REGIME_SLABS
    standard_deduction = (
        _NEW_REGIME_STANDARD_DEDUCTION if regime == "NEW"
        else _OLD_REGIME_STANDARD_DEDUCTION
    )

    income = max(0, taxable_income - standard_deduction)
    tax = 0.0

    for lower, upper, rate in slabs:
        if income <= lower:
            break
        taxable_in_slab = min(income, upper) - lower
        tax += taxable_in_slab * rate

    # 4% health and education cess
    tax *= 1.04
    return round(tax, 2)


# ---------------------------------------------------------------------------
# Locale Service
# ---------------------------------------------------------------------------


class LocaleService:
    """Business logic for locale-aware features."""

    def __init__(
        self,
        market_config_repo: MarketConfigRepository,
        currency_service: CurrencyService,
        cache_ttl: int = _DEFAULT_CACHE_TTL,
    ) -> None:
        self._market_repo = market_config_repo
        self._currency = currency_service
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[MarketConfig, float]] = {}

    # -- MarketConfig access with caching --

    async def get_market_config(self, region_code: str) -> MarketConfig | None:
        """Get a MarketConfig, using cache if available."""
        cached = self._get_cached(region_code)
        if cached:
            return cached

        config = await self._market_repo.get_by_region(region_code)
        if config:
            self._cache[region_code] = (config, time.time())
        return config

    def _get_cached(self, region_code: str) -> MarketConfig | None:
        entry = self._cache.get(region_code)
        if entry and (time.time() - entry[1]) < self._cache_ttl:
            return entry[0]
        return None

    def invalidate_cache(self, region_code: str) -> None:
        """Remove a region from cache. Called after admin update/delete."""
        self._cache.pop(region_code, None)

    # -- CTC Calculator --

    def decode_ctc(
        self,
        ctc_annual: float,
        city_type: str = "METRO",
        tax_regime: str = "NEW",
        variable_pay_pct: float = 0.0,
        joining_bonus: float = 0.0,
        retention_bonus: float = 0.0,
        esops_value: float = 0.0,
        insurance_value: float = 0.0,
    ) -> IndianCompensation:
        """
        Decompose an Indian CTC into components and compute in-hand monthly.

        CTC structure (default percentages):
            Basic = 40% of CTC
            HRA = 50% of Basic (METRO) or 40% (NON_METRO)
            Employer PF = 12% of Basic (capped at 1,800/month for EPS component)
            Employee PF = 12% of Basic
            Gratuity = 4.81% of Basic
            Variable = configured % of CTC
            Special Allowance = CTC - Basic - HRA - Employer PF - Gratuity - Variable
        """
        # Remove one-time components from annual recurring CTC
        recurring_ctc = ctc_annual - joining_bonus - retention_bonus - esops_value - insurance_value
        variable_pay = recurring_ctc * (variable_pay_pct / 100)
        fixed_ctc = recurring_ctc - variable_pay

        basic = fixed_ctc * 0.40
        hra_pct = 0.50 if city_type == "METRO" else 0.40
        hra = basic * hra_pct

        employer_pf = basic * 0.12
        employee_pf = basic * 0.12
        gratuity = basic * 0.0481

        # Special allowance is the remainder
        special_allowance = max(0, fixed_ctc - basic - hra - employer_pf - gratuity)

        # Taxable income (simplified)
        # Gross salary = basic + hra + special_allowance + variable_pay
        # Deductions: employee PF (exempt under both regimes up to limit)
        gross_salary = basic + hra + special_allowance + variable_pay
        taxable_income = gross_salary  # simplified; HRA exemption not computed
        tax_annual = _compute_tax(taxable_income, tax_regime)

        # In-hand monthly
        # Monthly = (Gross - Employee PF - Tax) / 12
        annual_net = gross_salary - employee_pf - tax_annual
        in_hand_monthly = round(annual_net / 12, 2)

        components = [
            CompensationComponent(name="Basic", value=round(basic, 2), pct_of_ctc=round(basic / ctc_annual * 100, 2)),
            CompensationComponent(name="HRA", value=round(hra, 2), pct_of_ctc=round(hra / ctc_annual * 100, 2)),
            CompensationComponent(name="Special Allowance", value=round(special_allowance, 2), pct_of_ctc=round(special_allowance / ctc_annual * 100, 2)),
            CompensationComponent(name="Employer PF", value=round(employer_pf, 2), pct_of_ctc=round(employer_pf / ctc_annual * 100, 2)),
            CompensationComponent(name="Employee PF", value=round(employee_pf, 2), pct_of_ctc=round(employee_pf / ctc_annual * 100, 2)),
            CompensationComponent(name="Gratuity", value=round(gratuity, 2), pct_of_ctc=round(gratuity / ctc_annual * 100, 2)),
        ]

        if variable_pay > 0:
            components.append(CompensationComponent(
                name="Variable Pay", value=round(variable_pay, 2),
                pct_of_ctc=round(variable_pay / ctc_annual * 100, 2),
            ))

        return IndianCompensation(
            ctc_annual=ctc_annual,
            basic=round(basic, 2),
            hra=round(hra, 2),
            special_allowance=round(special_allowance, 2),
            employer_pf=round(employer_pf, 2),
            employee_pf=round(employee_pf, 2),
            gratuity=round(gratuity, 2),
            variable_pay=round(variable_pay, 2),
            variable_payout_pct=variable_pay_pct,
            joining_bonus=joining_bonus,
            retention_bonus=retention_bonus,
            esops_value=esops_value,
            insurance_value=insurance_value,
            in_hand_monthly=in_hand_monthly,
            tax_annual_estimated=tax_annual,
            tax_regime=tax_regime,
            city_type=city_type,
            components=components,
        )

    # -- Salary Comparison --

    async def compare_salary(
        self,
        source_amount: float,
        source_currency: str,
        source_region: str,
        target_region: str,
    ) -> dict:
        """
        Compare compensation across two markets with PPP adjustment.

        Returns nominal conversion, PPP-adjusted equivalent, and confidence level.
        """
        source_config = await self.get_market_config(source_region)
        target_config = await self.get_market_config(target_region)

        if not source_config or not target_config:
            missing = source_region if not source_config else target_region
            return {"error": f"MarketConfig not found for {missing}"}

        target_currency = target_config.compensation_structure.currency_code
        conversion = await self._currency.convert(source_amount, source_currency, target_currency)

        source_ppp = source_config.compensation_structure.ppp_factor
        target_ppp = target_config.compensation_structure.ppp_factor
        ppp_adjusted = round(source_amount * (target_ppp / source_ppp), 2) if source_ppp > 0 else 0

        confidence = "HIGH"
        if not source_config or not target_config:
            confidence = "MEDIUM"
        if conversion["freshness"] == "stale":
            confidence = "LOW"

        return {
            "source": {
                "amount": source_amount,
                "currency": source_currency,
                "region": source_region,
            },
            "target": {
                "nominal_conversion": conversion["converted"],
                "currency": target_currency,
                "exchange_rate": conversion["rate"],
                "rate_freshness": conversion["freshness"],
            },
            "ppp_adjusted": {
                "equivalent": ppp_adjusted,
                "source_ppp_factor": source_ppp,
                "target_ppp_factor": target_ppp,
            },
            "confidence_level": confidence,
        }

    # -- Notice Period Calculators --

    def calculate_notice(self, action: str, **kwargs) -> dict:
        """
        Notice period calculator with three actions.

        Actions:
            JOINING_DATE: compute earliest joining date
            BUYOUT_COST: compute cost to buy out remaining days
            DEADLINE_MATCH: check if an offer deadline is feasible
        """
        if action == "JOINING_DATE":
            return self._calc_joining_date(**kwargs)
        elif action == "BUYOUT_COST":
            return self._calc_buyout_cost(**kwargs)
        elif action == "DEADLINE_MATCH":
            return self._calc_deadline_match(**kwargs)
        else:
            return {"error": f"Unknown action: {action}"}

    def _calc_joining_date(
        self,
        contractual_days: int = 0,
        served_days: int = 0,
        notice_start_date: str | datetime | None = None,
        **_kwargs,
    ) -> dict:
        if isinstance(notice_start_date, str):
            start = datetime.fromisoformat(notice_start_date)
        elif isinstance(notice_start_date, datetime):
            start = notice_start_date
        else:
            start = datetime.now(UTC)

        remaining = max(0, contractual_days - served_days)
        earliest = start + timedelta(days=remaining)

        return {
            "remaining_days": remaining,
            "earliest_joining_date": earliest.isoformat(),
            "notice_start_date": start.isoformat(),
        }

    def _calc_buyout_cost(
        self,
        monthly_basic: float = 0,
        remaining_days: int = 0,
        **_kwargs,
    ) -> dict:
        daily_rate = monthly_basic / 30 if monthly_basic > 0 else 0
        cost = round(daily_rate * remaining_days, 2)
        return {
            "buyout_cost": cost,
            "daily_rate": round(daily_rate, 2),
            "remaining_days": remaining_days,
        }

    def _calc_deadline_match(
        self,
        offer_deadline: str | datetime | None = None,
        contractual_days: int = 0,
        served_days: int = 0,
        notice_start_date: str | datetime | None = None,
        monthly_basic: float = 0,
        **_kwargs,
    ) -> dict:
        joining = self._calc_joining_date(contractual_days, served_days, notice_start_date)
        earliest = datetime.fromisoformat(joining["earliest_joining_date"])

        if isinstance(offer_deadline, str):
            deadline = datetime.fromisoformat(offer_deadline)
        elif isinstance(offer_deadline, datetime):
            deadline = offer_deadline
        else:
            return {"error": "offer_deadline is required"}

        # Make both offset-aware or offset-naive for comparison
        if earliest.tzinfo and not deadline.tzinfo:
            deadline = deadline.replace(tzinfo=UTC)
        elif not earliest.tzinfo and deadline.tzinfo:
            earliest = earliest.replace(tzinfo=UTC)

        gap_days = (earliest - deadline).days
        feasible = gap_days <= 0

        result = {
            "feasible": feasible,
            "earliest_joining_date": earliest.isoformat(),
            "offer_deadline": deadline.isoformat(),
            "gap_days": max(0, gap_days),
        }

        if not feasible and monthly_basic > 0:
            buyout = self._calc_buyout_cost(monthly_basic, gap_days)
            result["buyout_cost_to_bridge"] = buyout["buyout_cost"]

        return result
