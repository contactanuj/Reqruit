"""
Variable pay risk analysis — deterministic calculator (no LLM).

Looks up benchmark data for a company and computes expected actual payout,
risk level, and warnings for high variable pay percentages.
"""

from datetime import datetime

from src.repositories.variable_pay_benchmark_repository import VariablePayBenchmarkRepository


class VariablePayRiskResult:
    """Result of variable pay risk analysis."""

    def __init__(
        self,
        stated_variable_amount: float,
        estimated_actual_payout_pct: float,
        expected_actual_amount: float,
        risk_level: str,
        data_source: str,
        data_points_count: int | None,
        last_updated: datetime | None,
        confidence: str,
        high_variable_warning: str | None,
    ) -> None:
        self.stated_variable_amount = stated_variable_amount
        self.estimated_actual_payout_pct = estimated_actual_payout_pct
        self.expected_actual_amount = expected_actual_amount
        self.risk_level = risk_level
        self.data_source = data_source
        self.data_points_count = data_points_count
        self.last_updated = last_updated
        self.confidence = confidence
        self.high_variable_warning = high_variable_warning


class VariablePayRiskService:
    """Deterministic variable pay risk analysis using benchmark data."""

    INDUSTRY_DEFAULT_PAYOUT_PCT = 80.0

    def __init__(self, benchmark_repo: VariablePayBenchmarkRepository) -> None:
        self._repo = benchmark_repo

    async def analyze(
        self, company_name: str, variable_pay_pct: float, annual_ctc: float
    ) -> VariablePayRiskResult:
        """Analyze variable pay risk for the given parameters."""
        stated_amount = annual_ctc * (variable_pay_pct / 100)

        # Look up benchmark — company first, then industry fallback
        benchmark = await self._repo.get_by_company(company_name)
        if benchmark:
            data_source = "company_specific"
            payout_pct = benchmark.avg_payout_pct
            data_points = benchmark.data_points_count
            last_updated = benchmark.last_updated
        else:
            # Try industry average
            industry_benchmark = await self._repo.get_industry_average()
            if industry_benchmark:
                data_source = "industry_average"
                payout_pct = industry_benchmark.avg_payout_pct
                data_points = industry_benchmark.data_points_count
                last_updated = industry_benchmark.last_updated
            else:
                # Hardcoded fallback
                data_source = "industry_average"
                payout_pct = self.INDUSTRY_DEFAULT_PAYOUT_PCT
                data_points = None
                last_updated = None

        expected_amount = stated_amount * (payout_pct / 100)
        risk_level = self._assess_risk(payout_pct)
        confidence = self._assess_confidence(data_source, data_points)

        # Override for high variable percentage
        warning = None
        if variable_pay_pct > 30:
            warning = "Over 30% of your CTC is at-risk pay. Treat this as upside, not base."
            risk_level = "HIGH"

        return VariablePayRiskResult(
            stated_variable_amount=stated_amount,
            estimated_actual_payout_pct=payout_pct,
            expected_actual_amount=expected_amount,
            risk_level=risk_level,
            data_source=data_source,
            data_points_count=data_points,
            last_updated=last_updated,
            confidence=confidence,
            high_variable_warning=warning,
        )

    @staticmethod
    def _assess_risk(payout_pct: float) -> str:
        if payout_pct > 90:
            return "LOW"
        elif payout_pct >= 70:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _assess_confidence(data_source: str, data_points: int | None) -> str:
        if data_source == "industry_average":
            return "low"
        if data_points and data_points >= 50:
            return "high"
        return "medium"
