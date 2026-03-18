"""Tests for push notification routes."""

from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from src.api.dependencies import get_current_user, get_push_notification_service
from src.services.push_notification_service import DEFAULT_PREFERENCES


def _mock_user():
    user = MagicMock()
    user.id = "abc123"
    user.is_active = True
    return user


def _mock_service():
    """Create a mock PushNotificationService with async methods."""
    svc = AsyncMock()
    svc.register_subscription.return_value = {
        "status": "registered",
        "user_id": "abc123",
    }
    svc.unregister_subscription.return_value = {
        "status": "unregistered",
        "user_id": "abc123",
    }
    svc.get_preferences.return_value = dict(DEFAULT_PREFERENCES)
    svc.update_preferences.return_value = {**DEFAULT_PREFERENCES, "nudge": False}
    svc.send_notification.return_value = {
        "status": "skipped",
        "reason": "no_subscription",
    }
    return svc


def _setup_overrides(client: AsyncClient):
    """Set up dependency overrides for the test client."""
    mock_svc = _mock_service()
    client.app.dependency_overrides[get_current_user] = lambda: _mock_user()
    client.app.dependency_overrides[get_push_notification_service] = lambda: mock_svc
    return mock_svc


def _teardown_overrides(client: AsyncClient):
    """Remove dependency overrides after test."""
    client.app.dependency_overrides.pop(get_current_user, None)
    client.app.dependency_overrides.pop(get_push_notification_service, None)


class TestSubscribe:
    async def test_subscribe(self, client: AsyncClient):
        mock_svc = _setup_overrides(client)
        try:
            resp = await client.post(
                "/notifications/subscribe",
                json={"endpoint": "https://push.example.com", "keys": {"p256dh": "k", "auth": "a"}},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "registered"
            mock_svc.register_subscription.assert_awaited_once()
        finally:
            _teardown_overrides(client)

    async def test_unsubscribe(self, client: AsyncClient):
        mock_svc = _setup_overrides(client)
        try:
            resp = await client.delete("/notifications/subscribe")
            assert resp.status_code == 200
            assert resp.json()["status"] == "unregistered"
            mock_svc.unregister_subscription.assert_awaited_once()
        finally:
            _teardown_overrides(client)


class TestPreferences:
    async def test_get_preferences(self, client: AsyncClient):
        mock_svc = _setup_overrides(client)
        try:
            resp = await client.get("/notifications/preferences")
            assert resp.status_code == 200
            data = resp.json()
            assert "daily_shortlist" in data
            mock_svc.get_preferences.assert_awaited_once()
        finally:
            _teardown_overrides(client)

    async def test_update_preferences(self, client: AsyncClient):
        mock_svc = _setup_overrides(client)
        try:
            resp = await client.put(
                "/notifications/preferences",
                json={"nudge": False},
            )
            assert resp.status_code == 200
            assert resp.json()["nudge"] is False
            mock_svc.update_preferences.assert_awaited_once()
        finally:
            _teardown_overrides(client)


class TestSendTest:
    async def test_send_test_no_subscription(self, client: AsyncClient):
        mock_svc = _setup_overrides(client)
        try:
            resp = await client.post("/notifications/test")
            assert resp.status_code == 200
            assert resp.json()["status"] == "skipped"
            mock_svc.send_notification.assert_awaited_once()
        finally:
            _teardown_overrides(client)
