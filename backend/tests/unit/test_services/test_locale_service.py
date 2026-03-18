"""Tests for LocaleService — CTC calculator, salary comparison, notice period."""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.documents.market_config import CompensationStructure, MarketConfig
from src.repositories.market_config_repository import MarketConfigRepository
from src.services.currency_service import CurrencyService
from src.services.locale_service import LocaleService, _compute_tax


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_market_repo() -> MarketConfigRepository:
    repo = MagicMock(spec=MarketConfigRepository)
    repo.get_by_region = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_currency_service() -> CurrencyService:
    svc = MagicMock(spec=CurrencyService)
    svc.convert = AsyncMock(return_value={"converted": 83000.0, "rate": 83.0, "freshness": "fresh"})
    svc.get_rate = AsyncMock(return_value={"rate": 83.0, "freshness": "fresh"})
    return svc


@pytest.fixture
def service(mock_market_repo, mock_currency_service) -> LocaleService:
    return LocaleService(
        market_config_repo=mock_market_repo,
        currency_service=mock_currency_service,
        cache_ttl=3600,
    )


# ---------------------------------------------------------------------------
# Tax computation tests
# ---------------------------------------------------------------------------


class TestComputeTax:
    """Tests for the _compute_tax helper function."""

    def test_zero_income_no_tax(self) -> None:
        assert _compute_tax(0, "NEW") == 0.0

    def test_income_below_standard_deduction_new(self) -> None:
        # 75K standard deduction in new regime
        assert _compute_tax(50_000, "NEW") == 0.0

    def test_income_below_standard_deduction_old(self) -> None:
        # 50K standard deduction in old regime
        assert _compute_tax(40_000, "OLD") == 0.0

    def test_low_income_new_regime(self) -> None:
        # Taxable = 300_000 - 75_000 = 225_000 (all in 0% slab)
        assert _compute_tax(300_000, "NEW") == 0.0

    def test_new_regime_first_slab(self) -> None:
        # Taxable = 500_000. After std deduction (75K) = 425_000
        # 0-300K = 0, 300K-425K = 125K * 5% = 6250
        # + 4% cess = 6500
        tax = _compute_tax(500_000, "NEW")
        assert tax == round(6250 * 1.04, 2)

    def test_old_regime_first_slab(self) -> None:
        # Taxable = 400_000. After std deduction (50K) = 350_000
        # 0-250K = 0, 250K-350K = 100K * 5% = 5000
        # + 4% cess = 5200
        tax = _compute_tax(400_000, "OLD")
        assert tax == round(5000 * 1.04, 2)

    def test_high_income_new_regime(self) -> None:
        # Taxable = 2_000_000. After std deduction (75K) = 1_925_000
        # 0-300K: 0
        # 300K-700K: 400K * 5% = 20K
        # 700K-1M: 300K * 10% = 30K
        # 1M-1.2M: 200K * 15% = 30K
        # 1.2M-1.5M: 300K * 20% = 60K
        # 1.5M-1.925M: 425K * 30% = 127.5K
        # Total = 267,500 + 4% cess = 278,200
        tax = _compute_tax(2_000_000, "NEW")
        expected = round(267_500 * 1.04, 2)
        assert tax == expected

    def test_cess_is_4_percent(self) -> None:
        # Verify cess is applied to any non-zero tax
        tax_new = _compute_tax(1_000_000, "NEW")
        # After deduction: 925_000
        # 0-300K: 0, 300K-700K: 400K*5%=20K, 700K-925K: 225K*10%=22.5K
        # Total pre-cess = 42,500
        assert tax_new == round(42_500 * 1.04, 2)


# ---------------------------------------------------------------------------
# CTC Decoder tests
# ---------------------------------------------------------------------------


class TestDecodeCTC:
    """Tests for LocaleService.decode_ctc()."""

    def test_basic_is_40_percent(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.basic == 400_000.0

    def test_hra_metro_50_percent_of_basic(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, city_type="METRO")
        assert result.hra == 200_000.0

    def test_hra_non_metro_40_percent_of_basic(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, city_type="NON_METRO")
        assert result.hra == 160_000.0

    def test_employer_pf_12_percent_of_basic(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.employer_pf == 48_000.0

    def test_employee_pf_12_percent_of_basic(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.employee_pf == 48_000.0

    def test_gratuity_4_81_percent_of_basic(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.gratuity == round(400_000 * 0.0481, 2)

    def test_special_allowance_is_remainder(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        # CTC - Basic - HRA - PF - Gratuity = Special Allowance
        expected = 1_000_000 - 400_000 - 200_000 - 48_000 - round(400_000 * 0.0481, 2)
        assert result.special_allowance == round(expected, 2)

    def test_variable_pay_deducted_from_recurring(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, variable_pay_pct=10.0)
        assert result.variable_pay == 100_000.0

    def test_variable_pay_zero_by_default(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.variable_pay == 0.0

    def test_joining_bonus_excluded_from_recurring(self, service) -> None:
        result_no_bonus = service.decode_ctc(ctc_annual=1_000_000)
        result_with_bonus = service.decode_ctc(ctc_annual=1_100_000, joining_bonus=100_000)
        # Both should have same basic (based on recurring CTC of 1M)
        assert result_no_bonus.basic == result_with_bonus.basic

    def test_retention_bonus_excluded_from_recurring(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_200_000, retention_bonus=200_000)
        # Recurring = 1M, basic = 40% of 1M
        assert result.basic == 400_000.0

    def test_esops_excluded_from_recurring(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_500_000, esops_value=500_000)
        assert result.basic == 400_000.0

    def test_insurance_excluded_from_recurring(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_050_000, insurance_value=50_000)
        assert result.basic == 400_000.0

    def test_in_hand_monthly_positive(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.in_hand_monthly > 0

    def test_in_hand_monthly_less_than_gross_monthly(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_200_000)
        gross_monthly = (result.basic + result.hra + result.special_allowance) / 12
        assert result.in_hand_monthly < gross_monthly

    def test_tax_annual_positive_for_taxable_income(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert result.tax_annual_estimated > 0

    def test_tax_regime_stored(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, tax_regime="OLD")
        assert result.tax_regime == "OLD"

    def test_city_type_stored(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, city_type="NON_METRO")
        assert result.city_type == "NON_METRO"

    def test_components_list_populated(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        assert len(result.components) >= 6
        names = [c.name for c in result.components]
        assert "Basic" in names
        assert "HRA" in names
        assert "Employer PF" in names

    def test_variable_pay_component_added_when_nonzero(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, variable_pay_pct=15.0)
        names = [c.name for c in result.components]
        assert "Variable Pay" in names

    def test_variable_pay_component_absent_when_zero(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000, variable_pay_pct=0)
        names = [c.name for c in result.components]
        assert "Variable Pay" not in names

    def test_component_pct_of_ctc_sums_near_100(self, service) -> None:
        result = service.decode_ctc(ctc_annual=1_000_000)
        total_pct = sum(c.pct_of_ctc for c in result.components)
        # Should be close to 100% of the recurring CTC
        assert 95 < total_pct < 105

    def test_ctc_annual_stored(self, service) -> None:
        result = service.decode_ctc(ctc_annual=2_500_000)
        assert result.ctc_annual == 2_500_000

    def test_one_time_components_stored(self, service) -> None:
        result = service.decode_ctc(
            ctc_annual=1_500_000,
            joining_bonus=100_000,
            retention_bonus=50_000,
            esops_value=200_000,
            insurance_value=30_000,
        )
        assert result.joining_bonus == 100_000
        assert result.retention_bonus == 50_000
        assert result.esops_value == 200_000
        assert result.insurance_value == 30_000

    def test_old_regime_different_tax(self, service) -> None:
        result_new = service.decode_ctc(ctc_annual=2_000_000, tax_regime="NEW")
        result_old = service.decode_ctc(ctc_annual=2_000_000, tax_regime="OLD")
        assert result_new.tax_annual_estimated != result_old.tax_annual_estimated

    def test_low_ctc_minimal_tax(self, service) -> None:
        result = service.decode_ctc(ctc_annual=300_000)
        # At 300K CTC, taxable income is very low
        assert result.tax_annual_estimated == 0.0

    def test_special_allowance_non_negative(self, service) -> None:
        result = service.decode_ctc(ctc_annual=500_000)
        assert result.special_allowance >= 0


# ---------------------------------------------------------------------------
# MarketConfig caching tests
# ---------------------------------------------------------------------------


class TestMarketConfigCaching:
    """Tests for LocaleService market config caching."""

    async def test_cache_stores_config(self, service, mock_market_repo) -> None:
        config = MarketConfig(region_code="IN", region_name="India")
        mock_market_repo.get_by_region.return_value = config

        result = await service.get_market_config("IN")

        assert result is config
        assert "IN" in service._cache

    async def test_cache_hit_skips_db(self, service, mock_market_repo) -> None:
        config = MarketConfig(region_code="IN")
        service._cache["IN"] = (config, time.time())

        result = await service.get_market_config("IN")

        assert result is config
        mock_market_repo.get_by_region.assert_not_called()

    async def test_expired_cache_fetches_from_db(self, service, mock_market_repo) -> None:
        old_config = MarketConfig(region_code="IN")
        service._cache["IN"] = (old_config, time.time() - 7200)  # 2h ago, beyond 1h TTL

        new_config = MarketConfig(region_code="IN", region_name="India Updated")
        mock_market_repo.get_by_region.return_value = new_config

        result = await service.get_market_config("IN")

        assert result is new_config
        mock_market_repo.get_by_region.assert_called_once_with("IN")

    async def test_invalidate_cache_removes_entry(self, service) -> None:
        service._cache["IN"] = (MarketConfig(region_code="IN"), time.time())

        service.invalidate_cache("IN")

        assert "IN" not in service._cache

    async def test_invalidate_cache_nonexistent_key_no_error(self, service) -> None:
        service.invalidate_cache("ZZ")  # should not raise

    async def test_cache_miss_returns_none_for_unknown(self, service, mock_market_repo) -> None:
        mock_market_repo.get_by_region.return_value = None

        result = await service.get_market_config("ZZ")

        assert result is None
        assert "ZZ" not in service._cache


# ---------------------------------------------------------------------------
# Salary comparison tests
# ---------------------------------------------------------------------------


class TestCompareSalary:
    """Tests for LocaleService.compare_salary()."""

    async def test_compare_returns_structure(self, service, mock_market_repo, mock_currency_service) -> None:
        source = MarketConfig(
            region_code="IN",
            compensation_structure=CompensationStructure(ppp_factor=22.0, currency_code="INR"),
        )
        target = MarketConfig(
            region_code="US",
            compensation_structure=CompensationStructure(ppp_factor=1.0, currency_code="USD"),
        )
        mock_market_repo.get_by_region = AsyncMock(side_effect=lambda code: source if code == "IN" else target)

        result = await service.compare_salary(1_000_000, "INR", "IN", "US")

        assert "source" in result
        assert "target" in result
        assert "ppp_adjusted" in result
        assert "confidence_level" in result

    async def test_compare_ppp_adjustment(self, service, mock_market_repo, mock_currency_service) -> None:
        source = MarketConfig(
            region_code="IN",
            compensation_structure=CompensationStructure(ppp_factor=22.0, currency_code="INR"),
        )
        target = MarketConfig(
            region_code="US",
            compensation_structure=CompensationStructure(ppp_factor=1.0, currency_code="USD"),
        )
        mock_market_repo.get_by_region = AsyncMock(side_effect=lambda code: source if code == "IN" else target)

        result = await service.compare_salary(1_000_000, "INR", "IN", "US")

        # PPP adjusted = 1_000_000 * (1.0 / 22.0)
        expected_ppp = round(1_000_000 * (1.0 / 22.0), 2)
        assert result["ppp_adjusted"]["equivalent"] == expected_ppp

    async def test_compare_missing_source_config(self, service, mock_market_repo) -> None:
        mock_market_repo.get_by_region = AsyncMock(return_value=None)

        result = await service.compare_salary(1_000_000, "INR", "XX", "US")

        assert "error" in result

    async def test_compare_stale_rate_low_confidence(self, service, mock_market_repo, mock_currency_service) -> None:
        source = MarketConfig(
            region_code="IN",
            compensation_structure=CompensationStructure(ppp_factor=22.0, currency_code="INR"),
        )
        target = MarketConfig(
            region_code="US",
            compensation_structure=CompensationStructure(ppp_factor=1.0, currency_code="USD"),
        )
        mock_market_repo.get_by_region = AsyncMock(side_effect=lambda code: source if code == "IN" else target)
        mock_currency_service.convert.return_value = {"converted": 12000.0, "rate": 0.012, "freshness": "stale"}

        result = await service.compare_salary(1_000_000, "INR", "IN", "US")

        assert result["confidence_level"] == "LOW"


# ---------------------------------------------------------------------------
# Notice period tests
# ---------------------------------------------------------------------------


class TestCalculateNotice:
    """Tests for LocaleService notice period calculators."""

    def test_joining_date_basic(self, service) -> None:
        result = service.calculate_notice(
            action="JOINING_DATE",
            contractual_days=60,
            served_days=10,
        )
        assert result["remaining_days"] == 50
        assert "earliest_joining_date" in result

    def test_joining_date_all_served(self, service) -> None:
        result = service.calculate_notice(
            action="JOINING_DATE",
            contractual_days=30,
            served_days=30,
        )
        assert result["remaining_days"] == 0

    def test_joining_date_overserved(self, service) -> None:
        result = service.calculate_notice(
            action="JOINING_DATE",
            contractual_days=30,
            served_days=45,
        )
        assert result["remaining_days"] == 0

    def test_joining_date_with_start_date(self, service) -> None:
        result = service.calculate_notice(
            action="JOINING_DATE",
            contractual_days=30,
            served_days=0,
            notice_start_date="2026-03-01",
        )
        assert result["earliest_joining_date"].startswith("2026-03-31")

    def test_buyout_cost(self, service) -> None:
        result = service.calculate_notice(
            action="BUYOUT_COST",
            monthly_basic=60_000,
            remaining_days=30,
        )
        assert result["buyout_cost"] == 60_000.0
        assert result["daily_rate"] == 2000.0
        assert result["remaining_days"] == 30

    def test_buyout_cost_zero_basic(self, service) -> None:
        result = service.calculate_notice(
            action="BUYOUT_COST",
            monthly_basic=0,
            remaining_days=30,
        )
        assert result["buyout_cost"] == 0.0

    def test_deadline_match_feasible(self, service) -> None:
        future = (datetime.now(UTC) + timedelta(days=90)).isoformat()
        result = service.calculate_notice(
            action="DEADLINE_MATCH",
            contractual_days=30,
            served_days=0,
            offer_deadline=future,
        )
        assert result["feasible"] is True
        assert result["gap_days"] == 0

    def test_deadline_match_infeasible(self, service) -> None:
        past = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        result = service.calculate_notice(
            action="DEADLINE_MATCH",
            contractual_days=60,
            served_days=0,
            offer_deadline=past,
        )
        assert result["feasible"] is False
        assert result["gap_days"] > 0

    def test_deadline_match_infeasible_with_buyout(self, service) -> None:
        past = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        result = service.calculate_notice(
            action="DEADLINE_MATCH",
            contractual_days=60,
            served_days=0,
            offer_deadline=past,
            monthly_basic=60_000,
        )
        assert result["feasible"] is False
        assert "buyout_cost_to_bridge" in result

    def test_deadline_match_missing_deadline(self, service) -> None:
        result = service.calculate_notice(
            action="DEADLINE_MATCH",
            contractual_days=30,
            served_days=0,
        )
        assert "error" in result

    def test_unknown_action(self, service) -> None:
        result = service.calculate_notice(action="INVALID_ACTION")
        assert "error" in result
