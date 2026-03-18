"""
Tests for negotiation outcome, history, and benchmark endpoints on the offers router.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_offer_repository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_offer(user_id):
    offer = MagicMock()
    offer.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    offer.user_id = user_id
    offer.company_name = "Acme Corp"
    offer.role_title = "SDE-2"
    offer.total_comp_annual = 2500000.0
    return offer


def _make_offer_with_outcome(user_id, delta_pct=15.0, strategy="data_anchoring"):
    from datetime import datetime, timezone

    offer = _make_offer(user_id)
    outcome = MagicMock()
    outcome.initial_offer_total = 1000000.0
    outcome.final_offer_total = 1000000.0 + (1000000.0 * delta_pct / 100)
    outcome.delta_absolute = 1000000.0 * delta_pct / 100
    outcome.delta_percentage = delta_pct
    outcome.strategy_used = strategy
    outcome.outcome_notes = ""
    outcome.recorded_at = datetime(2025, 6, 1, tzinfo=timezone.utc)
    offer.negotiation_outcome = outcome
    return offer


def _override(app, user, offer_repo):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_offer_repository] = lambda: offer_repo


# ---------------------------------------------------------------------------
# POST /offers/{offer_id}/outcome
# ---------------------------------------------------------------------------


class TestRecordOutcome:

    async def test_outcome_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.record_outcome = AsyncMock(return_value=offer)
        _override(client.app, user, offer_repo)

        response = await client.post(
            f"/offers/{offer.id}/outcome",
            json={
                "initial_offer_total": 1000000,
                "final_offer_total": 1150000,
                "negotiation_strategy_used": "data_anchoring",
                "outcome_notes": "Used market data",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["delta_absolute"] == 150000.0
        assert data["delta_percentage"] == 15.0
        assert data["strategy_used"] == "data_anchoring"

    async def test_outcome_offer_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.record_outcome = AsyncMock(return_value=None)
        _override(client.app, user, offer_repo)

        response = await client.post(
            "/offers/cccccccccccccccccccccccc/outcome",
            json={
                "initial_offer_total": 1000000,
                "final_offer_total": 1150000,
                "negotiation_strategy_used": "data_anchoring",
            },
        )

        assert response.status_code == 404

    async def test_outcome_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/offers/cccccccccccccccccccccccc/outcome",
            json={
                "initial_offer_total": 1000000,
                "final_offer_total": 1150000,
                "negotiation_strategy_used": "data_anchoring",
            },
        )
        assert response.status_code in (401, 403)

    async def test_outcome_delta_computation_zero_initial(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.record_outcome = AsyncMock(return_value=offer)
        _override(client.app, user, offer_repo)

        response = await client.post(
            f"/offers/{offer.id}/outcome",
            json={
                "initial_offer_total": 0,
                "final_offer_total": 500000,
                "negotiation_strategy_used": "direct_ask",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["delta_percentage"] == 0.0  # avoid div by zero


# ---------------------------------------------------------------------------
# GET /offers/negotiation-history
# ---------------------------------------------------------------------------


class TestNegotiationHistory:

    async def test_history_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offers = [
            _make_offer_with_outcome(user.id, delta_pct=15.0, strategy="data_anchoring"),
            _make_offer_with_outcome(user.id, delta_pct=10.0, strategy="competing_offer"),
        ]
        offer_repo = MagicMock()
        offer_repo.get_negotiation_history = AsyncMock(return_value=offers)
        offer_repo.get_strategy_success_rates = AsyncMock(return_value={
            "data_anchoring": {"count": 1, "avg_delta_pct": 15.0, "success_rate": 1.0},
            "competing_offer": {"count": 1, "avg_delta_pct": 10.0, "success_rate": 1.0},
        })
        _override(client.app, user, offer_repo)

        response = await client.get("/offers/negotiation-history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["offers"]) == 2
        assert data["offers"][0]["delta_percentage"] == 15.0
        assert "data_anchoring" in data["strategy_stats"]
        assert data["improvement_trend"]["direction"] == "stable"

    async def test_history_empty(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_negotiation_history = AsyncMock(return_value=[])
        offer_repo.get_strategy_success_rates = AsyncMock(return_value={})
        _override(client.app, user, offer_repo)

        response = await client.get("/offers/negotiation-history")

        assert response.status_code == 200
        data = response.json()
        assert data["offers"] == []
        assert data["improvement_trend"]["direction"] == "stable"
        assert data["improvement_trend"]["avg_recent_delta_pct"] == 0.0

    async def test_history_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/offers/negotiation-history")
        assert response.status_code in (401, 403)

    async def test_history_improvement_trend_with_enough_data(self, client: AsyncClient) -> None:
        user = _make_user()
        # 6 outcomes: recent 3 have higher deltas than oldest 3
        offers = [
            _make_offer_with_outcome(user.id, delta_pct=20.0),
            _make_offer_with_outcome(user.id, delta_pct=18.0),
            _make_offer_with_outcome(user.id, delta_pct=22.0),
            _make_offer_with_outcome(user.id, delta_pct=5.0),
            _make_offer_with_outcome(user.id, delta_pct=3.0),
            _make_offer_with_outcome(user.id, delta_pct=4.0),
        ]
        offer_repo = MagicMock()
        offer_repo.get_negotiation_history = AsyncMock(return_value=offers)
        offer_repo.get_strategy_success_rates = AsyncMock(return_value={})
        _override(client.app, user, offer_repo)

        response = await client.get("/offers/negotiation-history")

        assert response.status_code == 200
        data = response.json()
        assert data["improvement_trend"]["direction"] == "improving"


# ---------------------------------------------------------------------------
# GET /offers/benchmarks
# ---------------------------------------------------------------------------


class TestBenchmarks:

    async def test_benchmarks_insufficient_data(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_anonymized_benchmarks = AsyncMock(
            return_value={"cohort_size": 5}
        )
        _override(client.app, user, offer_repo)

        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data_available"] is False
        assert data["cohort_size"] == 5
        assert "Insufficient" in data["message"]

    async def test_benchmarks_with_data(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_anonymized_benchmarks = AsyncMock(return_value={
            "cohort_size": 25,
            "avg_delta_pct": 12.5,
            "deltas": [10.0, 12.0, 15.0, 8.0, 14.0] * 5,
            "strategies": ["data_anchoring", "competing_offer"] * 12 + ["direct_ask"],
        })
        _override(client.app, user, offer_repo)

        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data_available"] is True
        assert data["cohort_size"] == 25
        assert data["confidence_level"] == "low"  # 10-30
        assert "avg_delta_pct" in data["benchmarks"]
        assert "median_delta_pct" in data["benchmarks"]
        assert "success_rate_by_strategy" in data["benchmarks"]

    async def test_benchmarks_no_user_id_in_response(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_anonymized_benchmarks = AsyncMock(return_value={
            "cohort_size": 15,
            "avg_delta_pct": 10.0,
            "deltas": [10.0] * 15,
            "strategies": ["data_anchoring"] * 15,
        })
        _override(client.app, user, offer_repo)

        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )

        data = response.json()
        # Must not contain any user identifiers
        assert "user_id" not in str(data)
        assert "distinct_users" not in str(data)

    async def test_benchmarks_confidence_levels(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        _override(client.app, user, offer_repo)

        # Medium confidence (30-100)
        offer_repo.get_anonymized_benchmarks = AsyncMock(return_value={
            "cohort_size": 50,
            "avg_delta_pct": 11.0,
            "deltas": [11.0] * 50,
            "strategies": ["data_anchoring"] * 50,
        })
        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )
        assert response.json()["confidence_level"] == "medium"

        # High confidence (100+)
        offer_repo.get_anonymized_benchmarks = AsyncMock(return_value={
            "cohort_size": 150,
            "avg_delta_pct": 13.0,
            "deltas": [13.0] * 150,
            "strategies": ["data_anchoring"] * 150,
        })
        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )
        assert response.json()["confidence_level"] == "high"

    async def test_benchmarks_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/offers/benchmarks?role_family=SDE-2&region=IN"
        )
        assert response.status_code in (401, 403)
