"""
Tests for offer comparison service — normalization, hidden costs, equity scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from src.services.offer_comparison import (
    ComparisonResult,
    _compute_equity_scenarios,
    _compute_hidden_costs,
    _detect_clawback,
    _normalize_offer,
    compare_offers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_component(name="Base Salary", value=2000000, **overrides):
    comp = MagicMock()
    comp.name = name
    comp.value = value
    comp.currency = overrides.get("currency", "INR")
    comp.frequency = overrides.get("frequency", "annual")
    comp.is_guaranteed = overrides.get("is_guaranteed", True)
    return comp


def _make_offer(
    offer_id="bbbbbbbbbbbbbbbbbbbbbbbb",
    company="Acme Corp",
    role="SDE-2",
    total=2500000,
    locale="IN",
    components=None,
    raw_text="",
):
    offer = MagicMock()
    offer.id = offer_id
    offer.company_name = company
    offer.role_title = role
    offer.total_comp_annual = total
    offer.locale_market = locale
    offer.raw_text = raw_text
    offer.components = components or [
        _make_component("Base Salary", 2000000),
        _make_component("Bonus", 500000, is_guaranteed=False),
    ]
    return offer


# ---------------------------------------------------------------------------
# _detect_clawback
# ---------------------------------------------------------------------------


class TestDetectClawback:

    def test_no_clawback(self):
        detected, details = _detect_clawback("Your CTC is 25 LPA. Congrats!")
        assert detected is False
        assert details == ""

    def test_clawback_detected(self):
        text = "If you leave within 1 year, you must repayment the joining bonus."
        detected, details = _detect_clawback(text)
        assert detected is True
        assert "repayment" in details

    def test_multiple_clawback_terms(self):
        text = "Clawback clause applies. Forfeiture of unvested stock."
        detected, details = _detect_clawback(text)
        assert detected is True
        assert "clawback" in details
        assert "forfeiture" in details


# ---------------------------------------------------------------------------
# _compute_equity_scenarios
# ---------------------------------------------------------------------------


class TestEquityScenarios:

    def test_no_equity(self):
        components = [_make_component("Base Salary", 2000000)]
        result = _compute_equity_scenarios(components)
        assert result is None

    def test_with_esops(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("ESOPs", 500000),
        ]
        result = _compute_equity_scenarios(components)
        assert result is not None
        assert result.conservative == 250000.0
        assert result.moderate == 500000.0
        assert result.aggressive == 1000000.0

    def test_with_rsus(self):
        components = [
            _make_component("RSU Grant", 1000000),
        ]
        result = _compute_equity_scenarios(components)
        assert result is not None
        assert result.conservative == 500000.0


# ---------------------------------------------------------------------------
# _compute_hidden_costs
# ---------------------------------------------------------------------------


class TestComputeHiddenCosts:

    def test_no_hidden_costs(self):
        offer = _make_offer(raw_text="Simple offer. 25 LPA CTC.")
        result = _compute_hidden_costs(offer)
        assert result.clawback_clauses_detected is False
        assert result.equity_cliff_risk_years == 0.0

    def test_clawback_in_raw_text(self):
        offer = _make_offer(raw_text="Repayment required if you leave within 1 year.")
        result = _compute_hidden_costs(offer)
        assert result.clawback_clauses_detected is True

    def test_equity_cliff_detected(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("ESOPs", 500000),
        ]
        offer = _make_offer(components=components)
        result = _compute_hidden_costs(offer)
        assert result.equity_cliff_risk_years == 1.0


# ---------------------------------------------------------------------------
# _normalize_offer
# ---------------------------------------------------------------------------


class TestNormalizeOffer:

    def test_basic_normalization(self):
        offer = _make_offer()
        result = _normalize_offer(offer)
        assert result.offer_id == "bbbbbbbbbbbbbbbbbbbbbbbb"
        assert result.company_name == "Acme Corp"
        assert result.total_annual_comp == 2500000
        assert result.in_hand_monthly == round(2500000 / 12, 2)

    def test_benefits_extracted(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("PF Contribution", 200000),
            _make_component("Insurance", 50000),
        ]
        offer = _make_offer(total=2250000, components=components)
        result = _normalize_offer(offer)
        assert result.benefits_value == 250000.0

    def test_growth_score_from_equity(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("ESOPs", 500000),
        ]
        offer = _make_offer(total=2500000, components=components)
        result = _normalize_offer(offer)
        assert result.growth_potential_score == 20.0

    def test_in_hand_monthly_explicit(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("In-Hand Monthly", 150000),
        ]
        offer = _make_offer(total=2000000, components=components)
        result = _normalize_offer(offer)
        assert result.in_hand_monthly == 150000


# ---------------------------------------------------------------------------
# compare_offers (integration with mocks)
# ---------------------------------------------------------------------------


class TestCompareOffers:

    async def test_same_market_comparison(self):
        offer1 = _make_offer(offer_id="aaa", company="CompanyA", total=2500000)
        offer2 = _make_offer(offer_id="bbb", company="CompanyB", total=3000000)
        locale_svc = MagicMock()

        with patch(
            "src.services.offer_comparison._generate_recommendation",
            new_callable=AsyncMock,
            return_value=("CompanyB", "Higher total comp"),
        ):
            result = await compare_offers([offer1, offer2], locale_svc, "user123")

        assert len(result.offers) == 2
        assert result.cross_market is False
        assert result.recommended_choice == "CompanyB"

    async def test_cross_market_triggers_ppp(self):
        offer1 = _make_offer(offer_id="aaa", locale="IN", total=2500000)
        offer2 = _make_offer(offer_id="bbb", locale="US", total=150000)
        locale_svc = MagicMock()
        locale_svc.compare_salary = AsyncMock(return_value={
            "ppp_adjusted": {"equivalent": 6000000},
        })

        with patch(
            "src.services.offer_comparison._generate_recommendation",
            new_callable=AsyncMock,
            return_value=("", ""),
        ):
            result = await compare_offers([offer1, offer2], locale_svc, "user123")

        assert result.cross_market is True
        # The US offer should have PPP-adjusted value
        us_offer = [o for o in result.offers if o.locale_market == "US"][0]
        assert us_offer.ppp_adjusted_annual == 6000000

    async def test_equity_scenarios_included(self):
        components = [
            _make_component("Base Salary", 2000000),
            _make_component("ESOPs", 500000),
        ]
        offer1 = _make_offer(offer_id="aaa", total=2500000, components=components)
        offer2 = _make_offer(offer_id="bbb", total=3000000)
        locale_svc = MagicMock()

        with patch(
            "src.services.offer_comparison._generate_recommendation",
            new_callable=AsyncMock,
            return_value=("", ""),
        ):
            result = await compare_offers([offer1, offer2], locale_svc, "user123")

        equity_offer = result.offers[0]
        assert equity_offer.equity_scenarios is not None
        assert equity_offer.equity_scenarios.conservative == 250000.0

        cash_offer = result.offers[1]
        assert cash_offer.equity_scenarios is None

    async def test_hidden_costs_included(self):
        offer1 = _make_offer(
            offer_id="aaa",
            raw_text="Clawback applies for 2 years",
        )
        offer2 = _make_offer(offer_id="bbb")
        locale_svc = MagicMock()

        with patch(
            "src.services.offer_comparison._generate_recommendation",
            new_callable=AsyncMock,
            return_value=("", ""),
        ):
            result = await compare_offers([offer1, offer2], locale_svc, "user123")

        clawback_offer = result.offers[0]
        assert clawback_offer.hidden_costs.clawback_clauses_detected is True
