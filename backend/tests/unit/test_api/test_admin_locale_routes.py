"""
Unit tests for admin locale routes.

Covers:
    GET    /admin/markets           — list all market configs
    GET    /admin/markets/{code}    — get specific market config
    POST   /admin/markets           — create market config
    PUT    /admin/markets/{code}    — update market config
    DELETE /admin/markets/{code}    — delete market config
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_market_config_repository
from src.db.documents.market_config import MarketConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "admin@example.com"
    user.is_active = True
    return user


def _make_market_config(region_code="IN", region_name="India"):
    config = MagicMock(spec=MarketConfig)
    config.region_code = region_code
    config.region_name = region_name
    config.version = 1
    config.model_dump.return_value = {
        "region_code": region_code,
        "region_name": region_name,
        "compensation_structure": {},
        "hiring_process": {},
        "resume_conventions": {},
        "job_platforms": [],
        "legal": {},
        "cultural": {},
        "infrastructure": {},
        "version": 1,
    }
    config.delete = AsyncMock()
    config.save = AsyncMock()
    return config


def _make_mock_repo():
    repo = MagicMock()
    repo.find_many = AsyncMock(return_value=[])
    repo.get_by_region = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# GET /admin/markets
# ---------------------------------------------------------------------------


class TestListMarkets:
    async def test_returns_empty_list(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.get("/admin/markets")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.clear()

    async def test_returns_configs(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        config = _make_market_config()
        repo = _make_mock_repo()
        repo.find_many.return_value = [config]

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.get("/admin/markets")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["region_code"] == "IN"
        finally:
            app.dependency_overrides.clear()

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/admin/markets")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /admin/markets/{code}
# ---------------------------------------------------------------------------


class TestGetMarket:
    async def test_found(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        config = _make_market_config()
        repo = _make_mock_repo()
        repo.get_by_region.return_value = config

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.get("/admin/markets/IN")
            assert response.status_code == 200
            assert response.json()["region_code"] == "IN"
        finally:
            app.dependency_overrides.clear()

    async def test_not_found(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.get("/admin/markets/ZZ")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /admin/markets
# ---------------------------------------------------------------------------


class TestCreateMarket:
    async def test_create_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        # Mock MarketConfig.insert to avoid DB call
        from unittest.mock import patch

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            with patch.object(MarketConfig, "insert", new_callable=AsyncMock):
                response = await client.post(
                    "/admin/markets",
                    json={"region_code": "DE", "region_name": "Germany"},
                )
            assert response.status_code == 201
            data = response.json()
            assert data["region_code"] == "DE"
            assert data["region_name"] == "Germany"
        finally:
            app.dependency_overrides.clear()

    async def test_create_duplicate_returns_409(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()
        repo.get_by_region.return_value = _make_market_config("DE", "Germany")

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/admin/markets",
                json={"region_code": "DE", "region_name": "Germany"},
            )
            assert response.status_code == 409
        finally:
            app.dependency_overrides.clear()

    async def test_create_invalid_region_code_returns_400(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.post(
                "/admin/markets",
                json={"region_code": "INDIA"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PUT /admin/markets/{code}
# ---------------------------------------------------------------------------


class TestUpdateMarket:
    async def test_update_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        config = _make_market_config()
        repo = _make_mock_repo()
        repo.get_by_region.return_value = config

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.put(
                "/admin/markets/IN",
                json={"region_name": "India Updated"},
            )
            assert response.status_code == 200
            config.save.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_update_increments_version(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        config = _make_market_config()
        assert config.version == 1
        repo = _make_mock_repo()
        repo.get_by_region.return_value = config

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            await client.put(
                "/admin/markets/IN",
                json={"region_name": "India v2"},
            )
            assert config.version == 2
        finally:
            app.dependency_overrides.clear()

    async def test_update_not_found(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.put(
                "/admin/markets/ZZ",
                json={"region_name": "Unknown"},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DELETE /admin/markets/{code}
# ---------------------------------------------------------------------------


class TestDeleteMarket:
    async def test_delete_success(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        config = _make_market_config()
        repo = _make_mock_repo()
        repo.get_by_region.return_value = config

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.delete("/admin/markets/IN")
            assert response.status_code == 204
            config.delete.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        repo = _make_mock_repo()

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_market_config_repository] = lambda: repo
        try:
            response = await client.delete("/admin/markets/ZZ")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
