"""
ESOP Valuation Service — deterministic calculator with Indian tax impact.

Pure arithmetic, no LLM call. Two-stage Indian ESOP taxation:
1. At Exercise: perquisite tax = (FMV - strike) * shares * slab_rate
2. At Sale: LTCG (>24 months) at 12.5% above 1.25L exemption,
           or STCG (<=24 months) at slab rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ExitScenario:
    scenario_name: str
    exit_multiplier: float
    exit_valuation: float
    price_per_share_at_exit: float
    pre_tax_value: float
    perquisite_tax: float
    capital_gains_tax: float
    capital_gains_type: str  # LTCG or STCG
    net_post_tax_value: float


@dataclass
class VestingTranche:
    tranche_number: int
    shares: int
    vesting_date: date
    cumulative_shares: int


@dataclass
class ESOPValuationResult:
    scenarios: list[ExitScenario]
    vesting_timeline: list[VestingTranche]
    cliff_warning: str | None
    cliff_date: date | None
    total_shares: int
    strike_price: float
    current_fmv: float


# Indian tax constants
LTCG_RATE = 0.125
LTCG_EXEMPTION = 125000.0  # 1.25L annual exemption
LTCG_HOLDING_MONTHS = 24


class ESOPValuationService:
    """Deterministic ESOP valuation with Indian tax calculations."""

    SCENARIOS = [
        ("Conservative", 1.5),
        ("Moderate", 3.0),
        ("Aggressive", 5.0),
    ]

    def valuate(
        self,
        shares: int,
        strike_price: float,
        current_company_valuation: float,
        cliff_months: int = 12,
        vesting_frequency: str = "monthly",
        vesting_total_months: int = 48,
        fmv_per_share: float | None = None,
        grant_date: date | None = None,
        tax_slab_rate: float = 0.3,
    ) -> ESOPValuationResult:
        """Compute 3 exit scenarios with Indian ESOP tax impact."""
        fmv = fmv_per_share if fmv_per_share is not None else strike_price
        effective_grant_date = grant_date or date.today()

        scenarios = []
        for name, multiplier in self.SCENARIOS:
            # At exit, the share price scales with the multiplier relative to current FMV
            price_per_share_at_exit = fmv * multiplier
            exit_valuation = current_company_valuation * multiplier

            scenario = self._calculate_exit_scenario(
                shares=shares,
                strike_price=strike_price,
                fmv_at_exercise=fmv,
                price_per_share_at_exit=price_per_share_at_exit,
                exit_valuation=exit_valuation,
                exit_multiplier=multiplier,
                scenario_name=name,
                holding_months=vesting_total_months,
                tax_slab_rate=tax_slab_rate,
            )
            scenarios.append(scenario)

        timeline = self._build_vesting_timeline(
            shares=shares,
            cliff_months=cliff_months,
            vesting_frequency=vesting_frequency,
            vesting_total_months=vesting_total_months,
            grant_date=effective_grant_date,
        )

        cliff_warning = None
        cliff_date = None
        if cliff_months > 0:
            cliff_warning = "No value realized before cliff"
            cliff_date = effective_grant_date + timedelta(days=cliff_months * 30)

        return ESOPValuationResult(
            scenarios=scenarios,
            vesting_timeline=timeline,
            cliff_warning=cliff_warning,
            cliff_date=cliff_date,
            total_shares=shares,
            strike_price=strike_price,
            current_fmv=fmv,
        )

    def _calculate_exit_scenario(
        self,
        shares: int,
        strike_price: float,
        fmv_at_exercise: float,
        price_per_share_at_exit: float,
        exit_valuation: float,
        exit_multiplier: float,
        scenario_name: str,
        holding_months: int,
        tax_slab_rate: float,
    ) -> ExitScenario:
        pre_tax_value = (price_per_share_at_exit - strike_price) * shares
        perquisite_tax = self._calculate_perquisite_tax(
            fmv_at_exercise, strike_price, shares, tax_slab_rate
        )
        cg_tax, cg_type = self._calculate_capital_gains_tax(
            price_per_share_at_exit, fmv_at_exercise, shares, holding_months, tax_slab_rate
        )
        net_post_tax = pre_tax_value - perquisite_tax - cg_tax

        return ExitScenario(
            scenario_name=scenario_name,
            exit_multiplier=exit_multiplier,
            exit_valuation=round(exit_valuation, 2),
            price_per_share_at_exit=round(price_per_share_at_exit, 2),
            pre_tax_value=round(max(pre_tax_value, 0), 2),
            perquisite_tax=round(max(perquisite_tax, 0), 2),
            capital_gains_tax=round(max(cg_tax, 0), 2),
            capital_gains_type=cg_type,
            net_post_tax_value=round(max(net_post_tax, 0), 2),
        )

    @staticmethod
    def _calculate_perquisite_tax(
        fmv_at_exercise: float,
        strike_price: float,
        shares: int,
        tax_slab_rate: float,
    ) -> float:
        """Perquisite = (FMV - strike) * shares, taxed at income slab rate."""
        perquisite = max(0, (fmv_at_exercise - strike_price) * shares)
        return perquisite * tax_slab_rate

    @staticmethod
    def _calculate_capital_gains_tax(
        sale_price: float,
        fmv_at_exercise: float,
        shares: int,
        holding_months: int,
        tax_slab_rate: float,
    ) -> tuple[float, str]:
        """Capital gains tax at sale — LTCG or STCG based on holding period."""
        capital_gain = (sale_price - fmv_at_exercise) * shares

        if capital_gain <= 0:
            return 0.0, "LTCG" if holding_months > LTCG_HOLDING_MONTHS else "STCG"

        if holding_months > LTCG_HOLDING_MONTHS:
            taxable = max(0, capital_gain - LTCG_EXEMPTION)
            return taxable * LTCG_RATE, "LTCG"
        else:
            return capital_gain * tax_slab_rate, "STCG"

    @staticmethod
    def _build_vesting_timeline(
        shares: int,
        cliff_months: int,
        vesting_frequency: str,
        vesting_total_months: int,
        grant_date: date,
    ) -> list[VestingTranche]:
        """Build vesting schedule with cliff and frequency."""
        if vesting_total_months <= 0 or shares <= 0:
            return []

        # Frequency in months
        freq_months = 3 if vesting_frequency == "quarterly" else 1

        # Number of vesting events after cliff
        post_cliff_months = vesting_total_months - cliff_months
        if post_cliff_months <= 0:
            # All shares vest at cliff
            cliff_date = grant_date + timedelta(days=cliff_months * 30)
            return [VestingTranche(
                tranche_number=1,
                shares=shares,
                vesting_date=cliff_date,
                cumulative_shares=shares,
            )]

        num_tranches = post_cliff_months // freq_months
        if num_tranches <= 0:
            num_tranches = 1

        # Cliff tranche gets proportional shares
        cliff_share_count = shares * cliff_months // vesting_total_months if cliff_months > 0 else 0
        remaining_shares = shares - cliff_share_count
        per_tranche = remaining_shares // num_tranches if num_tranches > 0 else remaining_shares

        timeline: list[VestingTranche] = []
        cumulative = 0
        tranche_num = 0

        # Cliff tranche
        if cliff_months > 0 and cliff_share_count > 0:
            tranche_num += 1
            cumulative += cliff_share_count
            cliff_date = grant_date + timedelta(days=cliff_months * 30)
            timeline.append(VestingTranche(
                tranche_number=tranche_num,
                shares=cliff_share_count,
                vesting_date=cliff_date,
                cumulative_shares=cumulative,
            ))

        # Post-cliff tranches
        for i in range(num_tranches):
            tranche_num += 1
            months_from_grant = cliff_months + (i + 1) * freq_months
            tranche_shares = per_tranche
            # Last tranche gets remainder
            if i == num_tranches - 1:
                tranche_shares = remaining_shares - per_tranche * (num_tranches - 1)
            cumulative += tranche_shares
            vest_date = grant_date + timedelta(days=months_from_grant * 30)
            timeline.append(VestingTranche(
                tranche_number=tranche_num,
                shares=tranche_shares,
                vesting_date=vest_date,
                cumulative_shares=cumulative,
            ))

        return timeline
