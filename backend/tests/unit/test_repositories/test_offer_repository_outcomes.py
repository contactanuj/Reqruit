"""
Tests for OfferRepository outcome, history, and aggregation methods.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.offer import NegotiationOutcome
from src.repositories.offer_repository import OfferRepository


def _make_repo() -> OfferRepository:
    return OfferRepository.__new__(OfferRepository)


def _uid() -> PydanticObjectId:
    return PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _oid() -> PydanticObjectId:
    return PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_outcome(delta_pct=15.0, strategy="data_anchoring") -> NegotiationOutcome:
    return NegotiationOutcome(
        initial_offer_total=1000000.0,
        final_offer_total=1000000.0 + (1000000.0 * delta_pct / 100),
        delta_absolute=1000000.0 * delta_pct / 100,
        delta_percentage=delta_pct,
        strategy_used=strategy,
    )


# ---------------------------------------------------------------------------
# record_outcome
# ---------------------------------------------------------------------------


async def test_record_outcome_success():
    repo = _make_repo()
    offer = MagicMock()
    offer.save = AsyncMock()
    repo.find_one = AsyncMock(return_value=offer)
    # Alias for get_by_user_and_id which calls find_one
    repo.get_by_user_and_id = AsyncMock(return_value=offer)

    outcome = _make_outcome()
    result = await repo.record_outcome(_oid(), _uid(), outcome, role_family="SDE-2")

    assert result is offer
    assert offer.negotiation_outcome == outcome
    assert offer.role_family == "SDE-2"
    offer.save.assert_called_once()


async def test_record_outcome_not_found():
    repo = _make_repo()
    repo.get_by_user_and_id = AsyncMock(return_value=None)

    outcome = _make_outcome()
    result = await repo.record_outcome(_oid(), _uid(), outcome)

    assert result is None


# ---------------------------------------------------------------------------
# get_negotiation_history
# ---------------------------------------------------------------------------


async def test_get_negotiation_history_delegates():
    repo = _make_repo()
    offers = [MagicMock(), MagicMock()]
    repo.find_many = AsyncMock(return_value=offers)

    result = await repo.get_negotiation_history(_uid())

    assert result == offers
    repo.find_many.assert_called_once_with(
        {"user_id": _uid(), "negotiation_outcome": {"$ne": None}},
        sort="-created_at",
    )


# ---------------------------------------------------------------------------
# get_strategy_success_rates
# ---------------------------------------------------------------------------


async def test_strategy_success_rates():
    repo = _make_repo()

    offer1 = MagicMock()
    offer1.negotiation_outcome = _make_outcome(delta_pct=15.0, strategy="data_anchoring")
    offer2 = MagicMock()
    offer2.negotiation_outcome = _make_outcome(delta_pct=-5.0, strategy="data_anchoring")
    offer3 = MagicMock()
    offer3.negotiation_outcome = _make_outcome(delta_pct=10.0, strategy="competing_offer")

    repo.find_many = AsyncMock(return_value=[offer1, offer2, offer3])

    result = await repo.get_strategy_success_rates(_uid())

    assert "data_anchoring" in result
    assert result["data_anchoring"]["count"] == 2
    assert result["data_anchoring"]["success_rate"] == 0.5  # 1 of 2 positive
    assert result["competing_offer"]["count"] == 1
    assert result["competing_offer"]["success_rate"] == 1.0


async def test_strategy_success_rates_empty():
    repo = _make_repo()
    repo.find_many = AsyncMock(return_value=[])

    result = await repo.get_strategy_success_rates(_uid())

    assert result == {}


# ---------------------------------------------------------------------------
# NegotiationOutcome model
# ---------------------------------------------------------------------------


def test_negotiation_outcome_defaults():
    outcome = NegotiationOutcome(
        initial_offer_total=1000000,
        final_offer_total=1150000,
        delta_absolute=150000,
        delta_percentage=15.0,
        strategy_used="data_anchoring",
    )
    assert outcome.outcome_notes == ""
    assert outcome.recorded_at is not None


def test_negotiation_outcome_delta_computation():
    initial = 1000000
    final = 1150000
    delta_abs = final - initial
    delta_pct = ((final - initial) / initial) * 100

    assert delta_abs == 150000
    assert delta_pct == 15.0
