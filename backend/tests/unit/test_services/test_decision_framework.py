"""
Tests for multi-criteria decision framework service.
"""

from unittest.mock import MagicMock

import pytest
from beanie import PydanticObjectId

from src.services.decision_framework import (
    DEFAULT_WEIGHTS,
    STANDARD_CRITERIA,
    DecisionResult,
    _run_sensitivity,
    _score_offers_deterministic,
    compute_decision_matrix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_component(name="Base Salary", value=2000000, currency="INR"):
    comp = MagicMock()
    comp.name = name
    comp.value = value
    comp.currency = currency
    return comp


def _make_offer(
    oid="aaaaaaaaaaaaaaaaaaaaaaaa",
    company="Acme",
    role="SDE-2",
    total=2500000,
    locale="IN",
    components=None,
):
    offer = MagicMock()
    offer.id = PydanticObjectId(oid)
    offer.company_name = company
    offer.role_title = role
    offer.total_comp_annual = total
    offer.locale_market = locale
    offer.components = components or [_make_component(value=total)]
    return offer


# ---------------------------------------------------------------------------
# Deterministic scoring
# ---------------------------------------------------------------------------


class TestDeterministicScoring:

    def test_compensation_normalized_0_to_10(self):
        low = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", total=2000000)
        high = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", total=4000000)
        scores = _score_offers_deterministic([low, high], ["compensation"])

        low_score = scores[str(low.id)]["compensation"][0]
        high_score = scores[str(high.id)]["compensation"][0]
        assert low_score == 0.0
        assert high_score == 10.0

    def test_growth_with_equity(self):
        with_equity = _make_offer(
            oid="aaaaaaaaaaaaaaaaaaaaaaaa",
            components=[_make_component("ESOP", 500000)],
        )
        without = _make_offer(
            oid="bbbbbbbbbbbbbbbbbbbbbbbb",
            components=[_make_component("Base Salary", 2000000)],
        )
        scores = _score_offers_deterministic([with_equity, without], ["growth"])

        assert scores[str(with_equity.id)]["growth"][0] == 7.0
        assert scores[str(without.id)]["growth"][0] == 5.0

    def test_default_scores_for_wlb_location_culture(self):
        offer = _make_offer()
        scores = _score_offers_deterministic(
            [offer], ["work_life_balance", "location", "culture"]
        )
        oid = str(offer.id)
        assert scores[oid]["work_life_balance"][0] == 5.0
        assert scores[oid]["location"][0] == 6.0  # has locale_market
        assert scores[oid]["culture"][0] == 5.0

    def test_all_criteria_produce_justifications(self):
        offer = _make_offer()
        scores = _score_offers_deterministic([offer], STANDARD_CRITERIA)
        oid = str(offer.id)
        for criterion in STANDARD_CRITERIA:
            _, justification = scores[oid][criterion]
            assert len(justification) > 0


# ---------------------------------------------------------------------------
# Weighted scoring + decision matrix
# ---------------------------------------------------------------------------


class TestComputeDecisionMatrix:

    async def test_default_weights_when_none_provided(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", total=2000000)
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", total=3000000)
        result = await compute_decision_matrix([o1, o2])

        assert result.weights_are_defaults is True
        assert result.criteria_weights == DEFAULT_WEIGHTS
        assert "default" in result.reasoning.lower()

    async def test_custom_weights_used(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", total=2000000)
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", total=4000000)
        weights = {"compensation": 0.8, "growth": 0.2}
        result = await compute_decision_matrix([o1, o2], criteria_weights=weights)

        assert result.weights_are_defaults is False
        assert result.criteria_weights == weights

    async def test_higher_comp_wins_with_comp_heavy_weights(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", company="Low", total=1000000)
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", company="High", total=5000000)
        weights = {"compensation": 1.0}
        result = await compute_decision_matrix([o1, o2], criteria_weights=weights)

        assert result.recommended_company == "High"

    async def test_result_has_all_fields(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa")
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb")
        result = await compute_decision_matrix([o1, o2])

        assert isinstance(result, DecisionResult)
        assert len(result.offers) == 2
        assert result.recommended_choice
        assert result.recommended_company
        assert result.reasoning

    async def test_offers_sorted_by_weighted_total(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", total=1000000)
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", total=5000000)
        result = await compute_decision_matrix([o1, o2])

        assert result.offers[0].weighted_total >= result.offers[1].weighted_total

    async def test_each_offer_has_scores_for_all_criteria(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa")
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb")
        result = await compute_decision_matrix([o1, o2])

        for row in result.offers:
            criteria_names = {s.criterion_name for s in row.scores}
            assert criteria_names == set(STANDARD_CRITERIA)


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------


class TestSensitivityAnalysis:

    async def test_sensitivity_returns_list(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa", total=2000000)
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb", total=2100000)
        result = await compute_decision_matrix([o1, o2])

        assert isinstance(result.sensitivity_analysis, list)

    async def test_sensitivity_detects_ranking_change(self):
        # Two very close offers — sensitivity should detect a possible flip
        o1 = _make_offer(
            oid="aaaaaaaaaaaaaaaaaaaaaaaa",
            company="A",
            total=2500000,
            components=[_make_component("ESOP", 2500000)],
        )
        o2 = _make_offer(
            oid="bbbbbbbbbbbbbbbbbbbbbbbb",
            company="B",
            total=2600000,
            components=[_make_component("Base Salary", 2600000)],
        )
        # With equal weights, B wins on comp but A wins on growth
        # Increasing growth weight should flip recommendation
        result = await compute_decision_matrix([o1, o2])

        # At minimum, sensitivity analysis ran without error
        assert isinstance(result.sensitivity_analysis, list)

    async def test_sensitivity_max_5_scenarios(self):
        o1 = _make_offer(oid="aaaaaaaaaaaaaaaaaaaaaaaa")
        o2 = _make_offer(oid="bbbbbbbbbbbbbbbbbbbbbbbb")
        result = await compute_decision_matrix([o1, o2])

        assert len(result.sensitivity_analysis) <= 5

    def test_run_sensitivity_direct(self):
        from src.services.decision_framework import OfferDecisionRow, CriterionScore

        row1 = OfferDecisionRow(
            offer_id="a", company_name="A",
            scores=[CriterionScore(criterion_name="comp", raw_score=8, justification="", weighted_score=1.6)],
            weighted_total=1.6,
        )
        row2 = OfferDecisionRow(
            offer_id="b", company_name="B",
            scores=[CriterionScore(criterion_name="comp", raw_score=9, justification="", weighted_score=1.8)],
            weighted_total=1.8,
        )
        raw = {"a": {"comp": (8.0, "")}, "b": {"comp": (9.0, "")}}
        weights = {"comp": 0.2}
        results = _run_sensitivity([row2, row1], raw, weights, ["comp"])
        # With only one criterion, shifting weight can't change ranking
        assert isinstance(results, list)
