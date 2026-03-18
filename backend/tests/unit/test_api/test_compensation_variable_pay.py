"""
Tests for the variable pay risk endpoint.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_variable_pay_benchmark_repository


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_benchmark_repo(company_benchmark=None, industry_benchmark=None):
    repo = MagicMock()
    repo.get_by_company = AsyncMock(return_value=company_benchmark)
    repo.get_industry_average = AsyncMock(return_value=industry_benchmark)
    return repo


def _make_benchmark(avg_payout_pct: float = 85.0, data_points: int = 100):
    b = MagicMock()
    b.avg_payout_pct = avg_payout_pct
    b.data_points_count = data_points
    b.last_updated = datetime(2025, 6, 1, tzinfo=timezone.utc)
    return b


def _override(app, user, benchmark_repo):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_variable_pay_benchmark_repository] = lambda: benchmark_repo


class TestVariablePayRiskEndpoint:

    async def test_200_with_company_benchmark(self, client: AsyncClient) -> None:
        user = _make_user()
        bench = _make_benchmark(avg_payout_pct=85.0, data_points=100)
        repo = _make_benchmark_repo(company_benchmark=bench)
        _override(client.app, user, repo)

        response = await client.post(
            "/compensation/variable-pay-risk",
            json={
                "company_name": "Acme Corp",
                "variable_pay_pct": 15.0,
                "annual_ctc": 2000000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stated_variable_amount"] == 300000.0
        assert data["data_source"] == "company_specific"
        assert data["risk_level"] == "MEDIUM"
        assert data["confidence"] == "high"

    async def test_200_industry_fallback(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = _make_benchmark_repo(company_benchmark=None, industry_benchmark=None)
        _override(client.app, user, repo)

        response = await client.post(
            "/compensation/variable-pay-risk",
            json={
                "company_name": "Unknown Corp",
                "variable_pay_pct": 15.0,
                "annual_ctc": 2000000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data_source"] == "industry_average"
        assert data["confidence"] == "low"

    async def test_high_variable_warning(self, client: AsyncClient) -> None:
        user = _make_user()
        bench = _make_benchmark(avg_payout_pct=95.0)
        repo = _make_benchmark_repo(company_benchmark=bench)
        _override(client.app, user, repo)

        response = await client.post(
            "/compensation/variable-pay-risk",
            json={
                "company_name": "Acme Corp",
                "variable_pay_pct": 40.0,
                "annual_ctc": 2000000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "HIGH"
        assert data["high_variable_warning"] is not None

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/compensation/variable-pay-risk",
            json={
                "company_name": "Acme",
                "variable_pay_pct": 15.0,
                "annual_ctc": 2000000,
            },
        )
        assert response.status_code in (401, 403)

    async def test_422_missing_required_fields(self, client: AsyncClient) -> None:
        user = _make_user()
        repo = _make_benchmark_repo()
        _override(client.app, user, repo)

        response = await client.post(
            "/compensation/variable-pay-risk",
            json={"company_name": "Acme"},
        )
        assert response.status_code == 422

    async def test_low_risk_company(self, client: AsyncClient) -> None:
        user = _make_user()
        bench = _make_benchmark(avg_payout_pct=95.0, data_points=200)
        repo = _make_benchmark_repo(company_benchmark=bench)
        _override(client.app, user, repo)

        response = await client.post(
            "/compensation/variable-pay-risk",
            json={
                "company_name": "Good Corp",
                "variable_pay_pct": 10.0,
                "annual_ctc": 1000000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "LOW"
        assert data["high_variable_warning"] is None
