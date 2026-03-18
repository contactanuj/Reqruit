"""
Tests for ESOPValuationService — deterministic ESOP calculator with Indian tax impact.
"""

import time
from datetime import date

from src.services.esop_valuation_service import ESOPValuationService


def _svc() -> ESOPValuationService:
    return ESOPValuationService()


# ---------------------------------------------------------------------------
# Exit scenarios
# ---------------------------------------------------------------------------


class TestExitScenarios:

    def test_returns_3_scenarios(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        assert len(result.scenarios) == 3

    def test_conservative_uses_1_5x(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        s = result.scenarios[0]
        assert s.scenario_name == "Conservative"
        assert s.exit_multiplier == 1.5

    def test_moderate_uses_3x(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        s = result.scenarios[1]
        assert s.scenario_name == "Moderate"
        assert s.exit_multiplier == 3.0

    def test_aggressive_uses_5x(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        s = result.scenarios[2]
        assert s.scenario_name == "Aggressive"
        assert s.exit_multiplier == 5.0

    def test_pre_tax_value_computed(self):
        # 1000 shares, strike=100, FMV=100 (default), conservative=1.5x => exit price=150
        # pre_tax = (150-100)*1000 = 50000
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        s = result.scenarios[0]
        assert s.pre_tax_value == 50000.0

    def test_net_post_tax_equals_pre_tax_minus_taxes(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        for s in result.scenarios:
            expected = s.pre_tax_value - s.perquisite_tax - s.capital_gains_tax
            assert s.net_post_tax_value == round(max(expected, 0), 2)


# ---------------------------------------------------------------------------
# Perquisite tax
# ---------------------------------------------------------------------------


class TestPerquisiteTax:

    def test_perquisite_tax_basic(self):
        # FMV=100 (same as strike) => perquisite = 0
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        # All scenarios: FMV at exercise = strike (100) since no separate FMV provided
        # Perquisite = (100 - 100) * 1000 * 0.3 = 0
        for s in result.scenarios:
            assert s.perquisite_tax == 0.0

    def test_perquisite_tax_with_fmv_above_strike(self):
        # FMV=200, strike=100, shares=1000, slab=0.3
        # Perquisite = (200-100)*1000 = 100000, tax = 30000
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            fmv_per_share=200.0, tax_slab_rate=0.3,
        )
        for s in result.scenarios:
            assert s.perquisite_tax == 30000.0

    def test_zero_perquisite_when_fmv_equals_strike(self):
        result = _svc().valuate(
            shares=500, strike_price=50.0,
            current_company_valuation=5_000_000,
            fmv_per_share=50.0,
        )
        for s in result.scenarios:
            assert s.perquisite_tax == 0.0


# ---------------------------------------------------------------------------
# Capital gains tax
# ---------------------------------------------------------------------------


class TestCapitalGainsTax:

    def test_ltcg_for_long_holding(self):
        # Default vesting_total_months=48 > 24 => LTCG
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        for s in result.scenarios:
            assert s.capital_gains_type == "LTCG"

    def test_stcg_for_short_holding(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            vesting_total_months=12,
        )
        for s in result.scenarios:
            assert s.capital_gains_type == "STCG"

    def test_ltcg_exemption_applied(self):
        # 1000 shares, strike=100, FMV=100, Conservative 1.5x => exit=150
        # Capital gain = (150-100)*1000 = 50000
        # LTCG: taxable = max(0, 50000-125000) = 0 => tax = 0
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        conservative = result.scenarios[0]
        assert conservative.capital_gains_tax == 0.0  # Below 1.25L exemption

    def test_ltcg_tax_above_exemption(self):
        # 10000 shares, strike=100, FMV=100, moderate 3x => exit=300
        # CG = (300-100)*10000 = 2000000
        # Taxable = 2000000 - 125000 = 1875000
        # Tax = 1875000 * 0.125 = 234375
        result = _svc().valuate(
            shares=10000, strike_price=100.0,
            current_company_valuation=100_000_000,
        )
        moderate = result.scenarios[1]
        assert moderate.capital_gains_tax == 234375.0

    def test_negative_capital_gains_no_tax(self):
        # If exit valuation is less than FMV (e.g., company declines)
        # Use high FMV so exit price at 1.5x of strike is still below FMV
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            fmv_per_share=500.0,  # FMV much higher than exit price at 1.5x
        )
        conservative = result.scenarios[0]
        # Exit price = 500*1.5=750, FMV at exercise=500, CG=(750-500)*1000=250000
        # Actually positive. Let's test differently.
        # For true negative CG, we'd need exit < FMV which doesn't happen with multiplier >= 1
        # So test with the service method directly
        tax, cg_type = ESOPValuationService._calculate_capital_gains_tax(
            sale_price=80.0, fmv_at_exercise=100.0, shares=1000,
            holding_months=48, tax_slab_rate=0.3,
        )
        assert tax == 0.0
        assert cg_type == "LTCG"


# ---------------------------------------------------------------------------
# Vesting timeline
# ---------------------------------------------------------------------------


class TestVestingTimeline:

    def test_monthly_vesting_with_cliff(self):
        result = _svc().valuate(
            shares=4800, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=12, vesting_frequency="monthly",
            vesting_total_months=48,
        )
        timeline = result.vesting_timeline
        assert len(timeline) > 0
        # First tranche is cliff (12/48 = 25% = 1200 shares)
        assert timeline[0].shares == 1200
        # Last tranche should have cumulative = total
        assert timeline[-1].cumulative_shares == 4800

    def test_quarterly_vesting(self):
        result = _svc().valuate(
            shares=4800, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=12, vesting_frequency="quarterly",
            vesting_total_months=48,
        )
        timeline = result.vesting_timeline
        assert len(timeline) > 0
        # Post-cliff: 36 months / 3 = 12 quarterly tranches + 1 cliff = 13
        assert len(timeline) == 13
        assert timeline[-1].cumulative_shares == 4800

    def test_no_cliff(self):
        result = _svc().valuate(
            shares=1200, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=0, vesting_frequency="monthly",
            vesting_total_months=12,
        )
        timeline = result.vesting_timeline
        assert len(timeline) == 12
        assert timeline[-1].cumulative_shares == 1200


# ---------------------------------------------------------------------------
# Cliff warning
# ---------------------------------------------------------------------------


class TestCliffWarning:

    def test_cliff_warning_set(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=12,
        )
        assert result.cliff_warning == "No value realized before cliff"
        assert result.cliff_date is not None

    def test_no_cliff_warning(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=0,
        )
        assert result.cliff_warning is None
        assert result.cliff_date is None

    def test_cliff_date_correct(self):
        grant = date(2025, 1, 1)
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            cliff_months=12, grant_date=grant,
        )
        assert result.cliff_date is not None
        # ~12 months later (12*30 = 360 days)
        expected = date(2025, 12, 27)  # 2025-01-01 + 360 days
        assert result.cliff_date == expected


# ---------------------------------------------------------------------------
# FMV handling
# ---------------------------------------------------------------------------


class TestFMVHandling:

    def test_uses_provided_fmv(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
            fmv_per_share=200.0,
        )
        assert result.current_fmv == 200.0

    def test_uses_strike_as_fmv_fallback(self):
        result = _svc().valuate(
            shares=1000, strike_price=100.0,
            current_company_valuation=10_000_000,
        )
        assert result.current_fmv == 100.0


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:

    def test_completes_in_under_5_seconds(self):
        start = time.monotonic()
        _svc().valuate(
            shares=100000, strike_price=100.0,
            current_company_valuation=1_000_000_000,
            cliff_months=12, vesting_frequency="monthly",
            vesting_total_months=48,
        )
        duration = time.monotonic() - start
        assert duration < 5.0
