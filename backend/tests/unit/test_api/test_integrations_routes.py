"""Tests for integration routes: /integrations/*."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_integration_service
from src.core.exceptions import ConflictError, NotFoundError
from src.db.documents.integration_connection import (
    IntegrationProvider,
    IntegrationStatus,
)
from src.services.integration_service import IntegrationStatusResponse


def _make_user():
    user = MagicMock()
    user.id = "aaaaaaaaaaaaaaaaaaaaaaaa"
    user.email = "user@example.com"
    user.is_active = True
    return user


def _make_service():
    return MagicMock()


class TestGmailConnect:
    async def test_200_returns_redirect_url(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.initiate_connection.return_value = {
            "redirect_url": "https://accounts.google.com/auth?...",
            "state": "csrf-state-token",
        }

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.post("/integrations/gmail/connect")

        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert data["state"] == "csrf-state-token"

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.post("/integrations/gmail/connect")
        assert response.status_code in (401, 403)


class TestGmailCallback:
    async def test_201_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        conn = MagicMock()
        conn.provider = IntegrationProvider.GMAIL
        conn.status = IntegrationStatus.CONNECTED
        conn.connected_at = datetime(2026, 3, 16, tzinfo=UTC)
        mock_service.complete_connection = AsyncMock(return_value=conn)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.post(
            "/integrations/gmail/callback",
            json={"code": "auth-code", "state": "csrf-state"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["provider"] == "gmail"
        assert data["status"] == "connected"

    async def test_400_for_invalid_state(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        from src.core.exceptions import BusinessValidationError

        mock_service.complete_connection = AsyncMock(
            side_effect=BusinessValidationError(detail="Invalid or expired OAuth state parameter")
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.post(
            "/integrations/gmail/callback",
            json={"code": "code", "state": "bad-state"},
        )
        assert response.status_code == 422

    async def test_409_if_already_connected(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.complete_connection = AsyncMock(
            side_effect=ConflictError(detail="Provider gmail already connected")
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.post(
            "/integrations/gmail/callback",
            json={"code": "code", "state": "state"},
        )
        assert response.status_code == 409


class TestGmailDisconnect:
    async def test_204_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.disconnect = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.request(
            "DELETE",
            "/integrations/gmail",
            json={"purge": True},
        )
        assert response.status_code == 204

    async def test_204_purge_false(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.disconnect = AsyncMock(return_value=None)

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.request(
            "DELETE",
            "/integrations/gmail",
            json={"purge": False},
        )
        assert response.status_code == 204

    async def test_404_when_not_connected(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.disconnect = AsyncMock(
            side_effect=NotFoundError("IntegrationConnection")
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.request(
            "DELETE",
            "/integrations/gmail",
            json={"purge": True},
        )
        assert response.status_code == 404


class TestIntegrationStatus:
    async def test_200_returns_provider_list(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.get_all_statuses = AsyncMock(
            return_value=[
                IntegrationStatusResponse(
                    provider="gmail",
                    status="connected",
                    connected_at=datetime(2026, 3, 16, tzinfo=UTC),
                    last_synced_at=None,
                    scopes=["gmail.readonly"],
                )
            ]
        )

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.get("/integrations/status")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "gmail"
        assert data[0]["status"] == "connected"
        # No token fields in response
        assert "oauth_token" not in data[0]
        assert "refresh_token" not in data[0]

    async def test_200_empty_list(self, client: AsyncClient) -> None:
        user = _make_user()
        mock_service = _make_service()
        mock_service.get_all_statuses = AsyncMock(return_value=[])

        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.get("/integrations/status")

        assert response.status_code == 200
        assert response.json() == []

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        app = client.app  # type: ignore[attr-defined]
        app.dependency_overrides.pop(get_current_user, None)

        response = await client.get("/integrations/status")
        assert response.status_code in (401, 403)
