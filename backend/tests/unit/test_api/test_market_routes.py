"""Tests for /market/* endpoints — signals, company trajectory, disruption radar."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


class TestGetMarketSignals:
    async def test_200_returns_signals(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_signal = MagicMock()
        mock_signal.id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
        mock_signal.signal_type = "hiring_trend"
        mock_signal.severity = "info"
        mock_signal.title = "Tech hiring up 20%"
        mock_signal.description = "Hiring surge in Bangalore tech sector."
        mock_signal.industry = "tech"
        mock_signal.region = "IN"
        mock_signal.confidence = 0.8
        mock_signal.tags = ["hiring", "india"]

        with patch("src.api.routes.market.MarketSignalRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_for_user = AsyncMock(return_value=[mock_signal])

            response = await client.get("/market/signals")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["signal_type"] == "hiring_trend"
        assert data[0]["title"] == "Tech hiring up 20%"

    async def test_200_returns_empty_list(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.market.MarketSignalRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_for_user = AsyncMock(return_value=[])

            response = await client.get("/market/signals")

        assert response.status_code == 200
        assert response.json() == []

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.get("/market/signals")
        assert response.status_code in (401, 403)


class TestCompanyTrajectory:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.market.MarketSignalRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_industry = AsyncMock(return_value=[])

            response = await client.post("/market/company-trajectory", json={
                "company_name": "Acme Corp",
                "industry": "tech",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Acme Corp"
        assert data["trajectory"] == "stable"
        assert "confidence" in data


class TestDisruptionRadar:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.market.MarketSignalRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_industry = AsyncMock(return_value=[])

            response = await client.post("/market/disruption-radar", json={
                "industry": "tech",
            })

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
