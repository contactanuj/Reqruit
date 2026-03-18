"""
Tests for market positioning service — percentile computation and fallback logic.
"""

from unittest.mock import AsyncMock, MagicMock

from src.services.market_positioning import (
    MarketPositionResult,
    _compute_percentile,
    _confidence_level,
    _normalize_role_family,
    compute_market_position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_benchmark(**overrides):
    bm = MagicMock()
    bm.p25 = overrides.get("p25", 1500000)
    bm.p50 = overrides.get("p50", 2000000)
    bm.p75 = overrides.get("p75", 3000000)
    bm.p90 = overrides.get("p90", 4000000)
    bm.sample_size = overrides.get("sample_size", 100)
    bm.source = overrides.get("source", "AmbitionBox")
    bm.currency_code = overrides.get("currency_code", "INR")
    bm.updated_at = overrides.get("updated_at", None)
    bm.created_at = overrides.get("created_at", None)
    return bm


def _make_offer(**overrides):
    offer = MagicMock()
    offer.role_title = overrides.get("role_title", "SDE-2")
    offer.locale_market = overrides.get("locale_market", "IN")
    offer.total_comp_annual = overrides.get("total_comp_annual", 2500000.0)
    return offer


# ---------------------------------------------------------------------------
# _normalize_role_family
# ---------------------------------------------------------------------------


class TestNormalizeRoleFamily:

    def test_strips_senior_prefix(self):
        assert _normalize_role_family("Senior Software Engineer") == "Software Engineer"

    def test_strips_junior_prefix(self):
        assert _normalize_role_family("Junior Developer") == "Developer"

    def test_strips_level_suffix(self):
        assert _normalize_role_family("Software Engineer II") == "Software Engineer"

    def test_strips_numeric_suffix(self):
        assert _normalize_role_family("SDE-2") == "SDE"

    def test_strips_staff_prefix(self):
        assert _normalize_role_family("Staff Backend Engineer") == "Backend Engineer"

    def test_no_change_for_plain_role(self):
        assert _normalize_role_family("Product Manager") == "Product Manager"

    def test_returns_original_if_fully_stripped(self):
        # Edge case: role is entirely a prefix like "Senior"
        result = _normalize_role_family("Senior")
        assert result == "Senior"


# ---------------------------------------------------------------------------
# _compute_percentile
# ---------------------------------------------------------------------------


class TestComputePercentile:

    def test_at_p25(self):
        bm = _make_benchmark()
        assert _compute_percentile(1500000, bm) == 25.0

    def test_at_p50(self):
        bm = _make_benchmark()
        assert _compute_percentile(2000000, bm) == 50.0

    def test_at_p75(self):
        bm = _make_benchmark()
        assert _compute_percentile(3000000, bm) == 75.0

    def test_at_p90(self):
        bm = _make_benchmark()
        assert _compute_percentile(4000000, bm) == 90.0

    def test_between_p50_and_p75(self):
        bm = _make_benchmark()
        # 2500000 is halfway between p50 (2M) and p75 (3M) -> 62.5
        result = _compute_percentile(2500000, bm)
        assert result == 62.5

    def test_below_p25(self):
        bm = _make_benchmark()
        # 750000 is half of p25 (1.5M) -> 12.5
        result = _compute_percentile(750000, bm)
        assert result == 12.5

    def test_above_p90_capped_at_99(self):
        bm = _make_benchmark()
        # Way above p90
        result = _compute_percentile(10000000, bm)
        assert result == 99.0

    def test_zero_value(self):
        bm = _make_benchmark()
        result = _compute_percentile(0, bm)
        assert result == 0.0


# ---------------------------------------------------------------------------
# _confidence_level
# ---------------------------------------------------------------------------


class TestConfidenceLevel:

    def test_high_confidence(self):
        assert _confidence_level(50) == "HIGH"
        assert _confidence_level(100) == "HIGH"

    def test_medium_confidence(self):
        assert _confidence_level(10) == "MEDIUM"
        assert _confidence_level(49) == "MEDIUM"

    def test_low_confidence(self):
        assert _confidence_level(9) == "LOW"
        assert _confidence_level(0) == "LOW"


# ---------------------------------------------------------------------------
# compute_market_position (integration-style with mocked repo)
# ---------------------------------------------------------------------------


class TestComputeMarketPosition:

    async def test_exact_match(self):
        offer = _make_offer(total_comp_annual=2500000)
        benchmark = _make_benchmark()
        repo = MagicMock()
        repo.find_by_role_and_region = AsyncMock(return_value=benchmark)

        result = await compute_market_position(offer, repo)

        assert result.data_available is True
        assert result.market_percentile == 62.5
        assert result.approximate_match is False
        assert result.confidence_level == "HIGH"
        repo.find_by_role_and_region.assert_called_once_with("SDE-2", "IN")

    async def test_fallback_to_role_family(self):
        offer = _make_offer(role_title="Senior SDE-2", total_comp_annual=2500000)
        family_benchmark = _make_benchmark(sample_size=20)
        repo = MagicMock()
        repo.find_by_role_and_region = AsyncMock(return_value=None)
        repo.find_by_family_and_region = AsyncMock(return_value=family_benchmark)

        result = await compute_market_position(offer, repo)

        assert result.data_available is True
        assert result.approximate_match is True
        assert "role family" in result.approximate_match_explanation
        assert result.confidence_level == "MEDIUM"

    async def test_no_benchmark_found(self):
        offer = _make_offer(total_comp_annual=2500000)
        repo = MagicMock()
        repo.find_by_role_and_region = AsyncMock(return_value=None)
        repo.find_by_family_and_region = AsyncMock(return_value=None)

        result = await compute_market_position(offer, repo)

        assert result.data_available is False

    async def test_zero_comp_returns_no_data(self):
        offer = _make_offer(total_comp_annual=0)
        repo = MagicMock()

        result = await compute_market_position(offer, repo)

        assert result.data_available is False

    async def test_salary_range_in_result(self):
        offer = _make_offer(total_comp_annual=2000000)
        benchmark = _make_benchmark()
        repo = MagicMock()
        repo.find_by_role_and_region = AsyncMock(return_value=benchmark)

        result = await compute_market_position(offer, repo)

        assert result.salary_range["p25"] == 1500000
        assert result.salary_range["p50"] == 2000000
        assert result.salary_range["p75"] == 3000000
        assert result.salary_range["p90"] == 4000000
        assert result.salary_range["currency"] == "INR"
