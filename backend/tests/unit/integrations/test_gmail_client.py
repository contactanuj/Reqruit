"""Tests for GmailClient OAuth operations."""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.integrations.base_client import ExternalAPIError
from src.integrations.gmail_client import (
    GMAIL_SCOPES,
    GmailClient,
    OAuthError,
    OAuthTokenResponse,
)


def _client() -> GmailClient:
    return GmailClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:3000/callback",
    )


class TestGenerateAuthUrl:
    def test_includes_correct_scopes(self):
        client = _client()
        url = client.generate_auth_url(state="test-state")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        scope = params["scope"][0]
        for s in GMAIL_SCOPES:
            assert s in scope

    def test_includes_client_id(self):
        client = _client()
        url = client.generate_auth_url(state="s")
        assert "client_id=test-client-id" in url

    def test_includes_redirect_uri(self):
        client = _client()
        url = client.generate_auth_url(state="s")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["redirect_uri"][0] == "http://localhost:3000/callback"

    def test_includes_state(self):
        client = _client()
        url = client.generate_auth_url(state="my-csrf-state")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["state"][0] == "my-csrf-state"

    def test_includes_access_type_offline(self):
        client = _client()
        url = client.generate_auth_url(state="s")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["access_type"][0] == "offline"

    def test_includes_prompt_consent(self):
        client = _client()
        url = client.generate_auth_url(state="s")
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["prompt"][0] == "consent"

    def test_url_starts_with_google_auth(self):
        client = _client()
        url = client.generate_auth_url(state="s")
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")


class TestExchangeCode:
    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_success_returns_token_response(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.access",
            "refresh_token": "1//refresh",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
            "token_type": "Bearer",
        }
        mock_request.return_value = mock_response

        client = _client()
        result = await client.exchange_code("auth-code-123")

        assert isinstance(result, OAuthTokenResponse)
        assert result.access_token == "ya29.access"
        assert result.refresh_token == "1//refresh"
        assert result.expires_in == 3600

    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_invalid_grant_raises_oauth_error(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code has already been used",
        }
        mock_request.return_value = mock_response

        client = _client()
        with pytest.raises(OAuthError) as exc_info:
            await client.exchange_code("used-code")
        assert exc_info.value.error_code == "invalid_grant"

    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_network_error_raises_external_api_error(self, mock_request):
        mock_request.side_effect = ExternalAPIError(
            status_code=503, detail="Connection refused", provider="GmailClient"
        )

        client = _client()
        with pytest.raises(ExternalAPIError):
            await client.exchange_code("code")


class TestRevokeToken:
    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_success_returns_true(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = _client()
        result = await client.revoke_token("ya29.token")
        assert result is True

    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_already_revoked_returns_false(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_request.return_value = mock_response

        client = _client()
        result = await client.revoke_token("already-revoked")
        assert result is False

    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_network_error_returns_false(self, mock_request):
        mock_request.side_effect = ExternalAPIError(
            status_code=503, detail="timeout", provider="GmailClient"
        )

        client = _client()
        result = await client.revoke_token("token")
        assert result is False


class TestGetUserEmail:
    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_success_returns_email(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"emailAddress": "user@gmail.com"}
        mock_request.return_value = mock_response

        client = _client()
        email = await client.get_user_email("ya29.access")
        assert email == "user@gmail.com"

    @patch.object(GmailClient, "_request", new_callable=AsyncMock)
    async def test_failure_raises(self, mock_request):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        client = _client()
        with pytest.raises(ExternalAPIError):
            await client.get_user_email("expired-token")
