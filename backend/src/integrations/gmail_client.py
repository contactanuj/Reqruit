"""
Gmail OAuth client for authorization, token exchange, and revocation.

Handles the Google OAuth2 web-server flow:
1. Generate authorization URL → redirect user to Google consent
2. Exchange authorization code for access/refresh tokens
3. Revoke tokens on disconnect
4. Fetch user's Gmail profile to verify connection

All HTTP calls go through BaseExternalClient with circuit breaker.
"""

from urllib.parse import urlencode

import structlog
from pydantic import BaseModel

from src.integrations.base_client import BaseExternalClient, ExternalAPIError

logger = structlog.get_logger()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.metadata",
]


class OAuthTokenResponse(BaseModel):
    """Response from Google's token exchange endpoint."""

    access_token: str
    refresh_token: str | None = None
    expires_in: int
    scope: str
    token_type: str


class OAuthError(ExternalAPIError):
    """Raised for OAuth-specific errors from Google."""

    def __init__(self, error_code: str, detail: str) -> None:
        self.error_code = error_code
        super().__init__(status_code=400, detail=detail, provider="Gmail")


class GmailClient(BaseExternalClient):
    """Google OAuth2 + Gmail API client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        super().__init__()
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def generate_auth_url(self, state: str) -> str:
        """Build the Google OAuth2 authorization URL for user consent."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokenResponse:
        """Exchange an authorization code for access/refresh tokens."""
        logger.info("gmail_exchanging_code", oauth_token="[ENCRYPTED]")
        response = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri,
            },
        )
        if response.status_code != 200:
            data = response.json()
            error_code = data.get("error", "unknown")
            description = data.get("error_description", "Token exchange failed")
            raise OAuthError(error_code=error_code, detail=description)
        return OAuthTokenResponse(**response.json())

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResponse:
        """Exchange a refresh_token for a new access_token via Google's token endpoint."""
        logger.info("gmail_refreshing_token", oauth_token="[ENCRYPTED]")
        response = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            data = response.json()
            error_code = data.get("error", "unknown")
            description = data.get("error_description", "Token refresh failed")
            raise OAuthError(error_code=error_code, detail=description)
        return OAuthTokenResponse(**response.json())

    async def revoke_token(self, token: str) -> bool:
        """Revoke an OAuth token at Google. Returns True on success."""
        logger.info("gmail_revoking_token", oauth_token="[ENCRYPTED]")
        try:
            response = await self._request(
                "POST",
                GOOGLE_REVOKE_URL,
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return response.status_code == 200
        except ExternalAPIError:
            logger.warning("gmail_revoke_failed_gracefully")
            return False

    async def get_user_email(self, access_token: str) -> str:
        """Fetch the Gmail user's email address to verify the connection."""
        response = await self._request(
            "GET",
            GMAIL_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise ExternalAPIError(
                status_code=response.status_code,
                detail="Failed to fetch Gmail profile",
                provider="Gmail",
            )
        return response.json()["emailAddress"]
