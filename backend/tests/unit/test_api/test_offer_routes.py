"""
Tests for offer analysis API routes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_locale_service,
    get_offer_repository,
    get_salary_benchmark_repository,
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


def _make_offer(user_id, **overrides):
    offer = MagicMock()
    offer.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    offer.user_id = user_id
    offer.company_name = overrides.get("company_name", "Acme Corp")
    offer.role_title = overrides.get("role_title", "SDE-2")
    offer.total_comp_annual = overrides.get("total_comp_annual", 2500000.0)
    offer.locale_market = overrides.get("locale_market", "")
    offer.missing_fields = overrides.get("missing_fields", [])
    offer.suggestions = overrides.get("suggestions", [])
    return offer


def _make_agent_result(**overrides):
    return {
        "components": overrides.get("components", [
            {"name": "Base Salary", "value": 2000000, "frequency": "annual",
             "is_guaranteed": True, "confidence": "high"},
            {"name": "Bonus", "value": 500000, "frequency": "annual",
             "is_guaranteed": False, "confidence": "medium"},
        ]),
        "total_comp_annual": overrides.get("total_comp_annual", 2500000.0),
        "missing_fields": overrides.get("missing_fields", []),
        "suggestions": overrides.get("suggestions", []),
    }


def _override(app, user, offer_repo, locale_svc=None):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_offer_repository] = lambda: offer_repo
    if locale_svc is not None:
        app.dependency_overrides[get_locale_service] = lambda: locale_svc


# ---------------------------------------------------------------------------
# POST /offers/analyze
# ---------------------------------------------------------------------------


class TestAnalyzeOffer:

    async def test_analyze_offer_201(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        saved_offer = _make_offer(user.id)
        offer_repo.create = AsyncMock(return_value=saved_offer)
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        agent_result = _make_agent_result()

        with patch("src.api.routes.offers.OfferAnalystAgent") as MockAgent:
            mock_agent_instance = AsyncMock(return_value=agent_result)
            MockAgent.return_value = mock_agent_instance

            response = await client.post(
                "/offers/analyze",
                json={
                    "offer_text": "Your CTC is 25 LPA",
                    "company_name": "Acme Corp",
                    "role_title": "SDE-2",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["offer_id"] == str(saved_offer.id)
        assert data["company_name"] == "Acme Corp"
        assert data["total_comp_annual"] == 2500000.0
        assert len(data["components"]) == 2

    async def test_analyze_offer_requires_auth(self, client: AsyncClient) -> None:
        # No dependency overrides — auth will fail
        response = await client.post(
            "/offers/analyze",
            json={
                "offer_text": "Salary: 150k",
                "company_name": "BigCo",
                "role_title": "Engineer",
            },
        )
        # HTTPBearer returns 403 when no auth header present
        assert response.status_code in (401, 403)

    async def test_analyze_offer_missing_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        saved_offer = _make_offer(user.id, missing_fields=["insurance"])
        offer_repo.create = AsyncMock(return_value=saved_offer)
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        agent_result = _make_agent_result(
            missing_fields=["insurance"],
            suggestions=["Ask about health insurance"],
        )

        with patch("src.api.routes.offers.OfferAnalystAgent") as MockAgent:
            mock_agent_instance = AsyncMock(return_value=agent_result)
            MockAgent.return_value = mock_agent_instance

            response = await client.post(
                "/offers/analyze",
                json={
                    "offer_text": "Base: 20 LPA",
                    "company_name": "TestCo",
                    "role_title": "Dev",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "insurance" in data["missing_fields"]
        assert len(data["suggestions"]) == 1

    async def test_analyze_offer_persists_via_repo(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        saved_offer = _make_offer(user.id)
        offer_repo.create = AsyncMock(return_value=saved_offer)
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        agent_result = _make_agent_result()

        with patch("src.api.routes.offers.OfferAnalystAgent") as MockAgent:
            mock_agent_instance = AsyncMock(return_value=agent_result)
            MockAgent.return_value = mock_agent_instance

            await client.post(
                "/offers/analyze",
                json={
                    "offer_text": "CTC 25 LPA",
                    "company_name": "Acme",
                    "role_title": "SDE",
                },
            )

        offer_repo.create.assert_called_once()
        created_offer = offer_repo.create.call_args.args[0]
        assert created_offer.user_id == user.id
        assert created_offer.company_name == "Acme"

    async def test_analyze_offer_validation_error(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        # Missing required field company_name
        response = await client.post(
            "/offers/analyze",
            json={"offer_text": "some text", "role_title": "Dev"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Helpers for market-position tests
# ---------------------------------------------------------------------------


def _make_market_result(**overrides):
    result = MagicMock()
    result.market_percentile = overrides.get("market_percentile", 62.5)
    result.percentile_label = overrides.get(
        "percentile_label", "Your offer is at p63 for SDE-2 in IN"
    )
    result.salary_range = overrides.get("salary_range", {
        "p25": 1500000, "p50": 2000000, "p75": 3000000,
        "p90": 4000000, "currency": "INR",
    })
    result.confidence_level = overrides.get("confidence_level", "HIGH")
    result.data_source = overrides.get("data_source", "AmbitionBox")
    result.last_updated = overrides.get("last_updated", "2026-01-15T00:00:00")
    result.approximate_match = overrides.get("approximate_match", False)
    result.approximate_match_explanation = overrides.get(
        "approximate_match_explanation", None
    )
    result.data_available = overrides.get("data_available", True)
    return result


def _override_market(app, user, offer_repo, benchmark_repo):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_offer_repository] = lambda: offer_repo
    app.dependency_overrides[get_salary_benchmark_repository] = lambda: benchmark_repo


# ---------------------------------------------------------------------------
# GET /offers/{offer_id}/market-position
# ---------------------------------------------------------------------------


class TestGetMarketPosition:

    async def test_market_position_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id, locale_market="IN")
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=offer)
        benchmark_repo = MagicMock()
        _override_market(client.app, user, offer_repo, benchmark_repo)

        market_result = _make_market_result()

        with patch(
            "src.api.routes.offers.compute_market_position",
            new_callable=AsyncMock,
            return_value=market_result,
        ):
            response = await client.get(
                f"/offers/{offer.id}/market-position",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["market_percentile"] == 62.5
        assert data["confidence_level"] == "HIGH"
        assert data["data_available"] is True
        assert data["approximate_match"] is False
        assert "p25" in data["salary_range"]

    async def test_market_position_not_found(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=None)
        benchmark_repo = MagicMock()
        _override_market(client.app, user, offer_repo, benchmark_repo)

        fake_id = "cccccccccccccccccccccccc"
        response = await client.get(f"/offers/{fake_id}/market-position")

        assert response.status_code == 404

    async def test_market_position_requires_auth(self, client: AsyncClient) -> None:
        fake_id = "cccccccccccccccccccccccc"
        response = await client.get(f"/offers/{fake_id}/market-position")
        assert response.status_code in (401, 403)

    async def test_market_position_approximate_match(
        self, client: AsyncClient
    ) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=offer)
        benchmark_repo = MagicMock()
        _override_market(client.app, user, offer_repo, benchmark_repo)

        market_result = _make_market_result(
            approximate_match=True,
            approximate_match_explanation=(
                "No exact data for 'SDE-2'. Using 'SDE' role family benchmarks."
            ),
        )

        with patch(
            "src.api.routes.offers.compute_market_position",
            new_callable=AsyncMock,
            return_value=market_result,
        ):
            response = await client.get(f"/offers/{offer.id}/market-position")

        assert response.status_code == 200
        data = response.json()
        assert data["approximate_match"] is True
        assert "SDE" in data["approximate_match_explanation"]

    async def test_market_position_no_data(self, client: AsyncClient) -> None:
        user = _make_user()
        offer = _make_offer(user.id)
        offer_repo = MagicMock()
        offer_repo.get_by_user_and_id = AsyncMock(return_value=offer)
        benchmark_repo = MagicMock()
        _override_market(client.app, user, offer_repo, benchmark_repo)

        market_result = _make_market_result(
            data_available=False,
            market_percentile=0.0,
            percentile_label="",
            salary_range={},
            confidence_level="LOW",
            data_source="",
            last_updated="",
        )

        with patch(
            "src.api.routes.offers.compute_market_position",
            new_callable=AsyncMock,
            return_value=market_result,
        ):
            response = await client.get(f"/offers/{offer.id}/market-position")

        assert response.status_code == 200
        data = response.json()
        assert data["data_available"] is False


# ---------------------------------------------------------------------------
# Helpers for compare tests
# ---------------------------------------------------------------------------


def _make_comparison_result(**overrides):
    from src.services.offer_comparison import (
        ComparisonResult,
        HiddenCostAnalysis,
        NormalizedOffer,
    )

    offers = overrides.get("offers", [
        NormalizedOffer(
            offer_id="aaaaaaaaaaaaaaaaaaaaaaaa",
            company_name="CompanyA",
            role_title="SDE-2",
            in_hand_monthly=200000,
            total_annual_comp=2500000,
            benefits_value=100000,
            growth_potential_score=0.0,
            locale_market="IN",
            currency="INR",
            components=[],
            hidden_costs=HiddenCostAnalysis(),
        ),
        NormalizedOffer(
            offer_id="bbbbbbbbbbbbbbbbbbbbbbbb",
            company_name="CompanyB",
            role_title="SDE-2",
            in_hand_monthly=250000,
            total_annual_comp=3000000,
            benefits_value=150000,
            growth_potential_score=10.0,
            locale_market="IN",
            currency="INR",
            components=[],
            hidden_costs=HiddenCostAnalysis(),
        ),
    ])
    return ComparisonResult(
        offers=offers,
        cross_market=overrides.get("cross_market", False),
        recommended_choice=overrides.get("recommended_choice", "CompanyB"),
        reasoning=overrides.get("reasoning", "Higher total comp"),
    )


# ---------------------------------------------------------------------------
# POST /offers/compare
# ---------------------------------------------------------------------------


class TestCompareOffers:

    async def test_compare_offers_200(self, client: AsyncClient) -> None:
        user = _make_user()
        offer1 = _make_offer(user.id, company_name="CompanyA")
        offer2 = _make_offer(user.id, company_name="CompanyB")
        offer2.id = PydanticObjectId("cccccccccccccccccccccccc")
        offer_repo = MagicMock()
        offer_repo.compare_offers = AsyncMock(return_value=[offer1, offer2])
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        comparison_result = _make_comparison_result()

        with patch(
            "src.api.routes.offers.compare_offers",
            new_callable=AsyncMock,
            return_value=comparison_result,
        ):
            response = await client.post(
                "/offers/compare",
                json={"offer_ids": [str(offer1.id), str(offer2.id)]},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["offers"]) == 2
        assert data["recommended_choice"] == "CompanyB"
        assert data["cross_market"] is False

    async def test_compare_fewer_than_2_offers_422(
        self, client: AsyncClient
    ) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        response = await client.post(
            "/offers/compare",
            json={"offer_ids": ["aaaaaaaaaaaaaaaaaaaaaaaa"]},
        )

        assert response.status_code == 422

    async def test_compare_missing_offer_404(self, client: AsyncClient) -> None:
        user = _make_user()
        offer_repo = MagicMock()
        # Repo returns fewer offers than requested
        offer_repo.compare_offers = AsyncMock(return_value=[_make_offer(user.id)])
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        response = await client.post(
            "/offers/compare",
            json={
                "offer_ids": [
                    "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbb",
                ],
            },
        )

        assert response.status_code == 404

    async def test_compare_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/offers/compare",
            json={
                "offer_ids": [
                    "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbb",
                ],
            },
        )
        assert response.status_code in (401, 403)

    async def test_compare_includes_hidden_costs(
        self, client: AsyncClient
    ) -> None:
        user = _make_user()
        offer1 = _make_offer(user.id)
        offer2 = _make_offer(user.id)
        offer2.id = PydanticObjectId("cccccccccccccccccccccccc")
        offer_repo = MagicMock()
        offer_repo.compare_offers = AsyncMock(return_value=[offer1, offer2])
        locale_svc = MagicMock()
        _override(client.app, user, offer_repo, locale_svc)

        comparison_result = _make_comparison_result()

        with patch(
            "src.api.routes.offers.compare_offers",
            new_callable=AsyncMock,
            return_value=comparison_result,
        ):
            response = await client.post(
                "/offers/compare",
                json={"offer_ids": [str(offer1.id), str(offer2.id)]},
            )

        assert response.status_code == 200
        data = response.json()
        for offer_data in data["offers"]:
            assert "hidden_costs" in offer_data
            assert "clawback_clauses_detected" in offer_data["hidden_costs"]
