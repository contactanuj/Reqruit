"""Tests for GoogleCalendarClient OAuth and event listing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.google_calendar_client import (
    CalendarOAuthError,
    GoogleCalendarClient,
    SyncTokenInvalidError,
)


def _client():
    return GoogleCalendarClient(
        client_id="cal-client-id",
        client_secret="cal-secret",
        redirect_uri="https://app.example.com/callback/calendar",
    )


class TestGenerateAuthUrl:
    def test_includes_calendar_scope(self):
        url = _client().generate_auth_url("state123")
        assert "calendar.readonly" in url
        assert "state123" in url

    def test_includes_client_id_and_redirect(self):
        url = _client().generate_auth_url("s")
        assert "cal-client-id" in url
        assert "callback%2Fcalendar" in url or "callback/calendar" in url

    def test_includes_offline_access(self):
        url = _client().generate_auth_url("s")
        assert "access_type=offline" in url

    def test_includes_consent_prompt(self):
        url = _client().generate_auth_url("s")
        assert "prompt=consent" in url


class TestExchangeCode:
    async def test_returns_token_response(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.cal",
            "refresh_token": "1//cal_refresh",
            "expires_in": 3600,
            "scope": "calendar.readonly",
            "token_type": "Bearer",
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.exchange_code("auth_code")

        assert result.access_token == "ya29.cal"
        assert result.refresh_token == "1//cal_refresh"
        assert result.expires_in == 3600

    async def test_raises_on_error(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code already used",
        }

        with (
            patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response),
            pytest.raises(CalendarOAuthError),
        ):
            await client.exchange_code("bad_code")


class TestListEvents:
    async def test_returns_parsed_events(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "evt1",
                    "summary": "Technical Interview",
                    "start": {"dateTime": "2026-03-20T10:00:00Z"},
                    "end": {"dateTime": "2026-03-20T11:00:00Z"},
                    "organizer": {"email": "hr@google.com"},
                    "attendees": [
                        {"email": "candidate@gmail.com"},
                        {"email": "recruiter@google.com"},
                    ],
                    "status": "confirmed",
                }
            ],
            "nextSyncToken": "sync_abc",
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.list_events("token123")

        assert len(result.events) == 1
        assert result.events[0].event_id == "evt1"
        assert result.events[0].summary == "Technical Interview"
        assert result.events[0].organizer_email == "hr@google.com"
        assert len(result.events[0].attendees) == 2
        assert result.next_sync_token == "sync_abc"

    async def test_handles_pagination(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [],
            "nextPageToken": "page2",
        }

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.list_events("token", page_token="page1")

        assert result.next_page_token == "page2"

    async def test_sync_token_sends_incremental(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [], "nextSyncToken": "new_sync"}

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client.list_events("token", sync_token="old_sync")

        call_kwargs = mock_req.call_args
        assert "syncToken" in call_kwargs.kwargs.get("params", {})

    async def test_410_raises_sync_token_invalid(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 410

        with (
            patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response),
            pytest.raises(SyncTokenInvalidError),
        ):
            await client.list_events("token", sync_token="expired")

    async def test_401_raises_token_expired(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 401

        from src.integrations.base_client import ExternalAPIError

        with (
            patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response),
            pytest.raises(ExternalAPIError, match="expired"),
        ):
            await client.list_events("token")


class TestRevokeToken:
    async def test_revoke_success(self):
        client = _client()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.revoke_token("token123")

        assert result is True

    async def test_revoke_failure_returns_false(self):
        client = _client()

        from src.integrations.base_client import ExternalAPIError

        with patch.object(
            client, "_request", new_callable=AsyncMock,
            side_effect=ExternalAPIError(500, "fail", "GoogleCalendar"),
        ):
            result = await client.revoke_token("token123")

        assert result is False
