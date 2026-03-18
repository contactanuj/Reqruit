"""
Google Calendar OAuth client for authorization, token exchange, and event listing.

Handles the Google OAuth2 web-server flow for Calendar:
1. Generate authorization URL → redirect user to Google consent
2. Exchange authorization code for access/refresh tokens
3. List calendar events for interview detection
4. Revoke tokens on disconnect

All HTTP calls go through BaseExternalClient with circuit breaker.
"""

from datetime import datetime
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel

from src.integrations.base_client import BaseExternalClient, ExternalAPIError

logger = structlog.get_logger()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]


class CalendarEvent(BaseModel):
    """A single calendar event from Google Calendar API."""

    event_id: str
    summary: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    organizer_email: str | None = None
    attendees: list[str] = []
    location: str | None = None
    status: str = "confirmed"


class CalendarEventsResponse(BaseModel):
    """Response from Google Calendar events.list."""

    events: list[CalendarEvent] = []
    next_page_token: str | None = None
    next_sync_token: str | None = None


class SyncTokenInvalidError(ExternalAPIError):
    """Raised when Google returns 410 Gone for an expired syncToken."""

    def __init__(self) -> None:
        super().__init__(
            status_code=410,
            detail="Sync token expired — full resync required",
            provider="GoogleCalendar",
        )


class CalendarOAuthError(ExternalAPIError):
    """Raised for OAuth-specific errors from Google Calendar."""

    def __init__(self, error_code: str, detail: str) -> None:
        self.error_code = error_code
        super().__init__(status_code=400, detail=detail, provider="GoogleCalendar")


class GoogleCalendarClient(BaseExternalClient):
    """Google OAuth2 + Calendar API client."""

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
        """Build the Google OAuth2 authorization URL for calendar consent."""
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(CALENDAR_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str):
        """Exchange an authorization code for access/refresh tokens."""
        from src.integrations.gmail_client import OAuthTokenResponse

        logger.info("calendar_exchanging_code", oauth_token="[ENCRYPTED]")
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
            raise CalendarOAuthError(error_code=error_code, detail=description)
        return OAuthTokenResponse(**response.json())

    async def refresh_access_token(self, refresh_token: str):
        """Exchange a refresh_token for a new access_token via Google's token endpoint."""
        from src.integrations.gmail_client import OAuthTokenResponse

        logger.info("calendar_refreshing_token", oauth_token="[ENCRYPTED]")
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
            raise CalendarOAuthError(error_code=error_code, detail=description)
        return OAuthTokenResponse(**response.json())

    async def list_events(
        self,
        access_token: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        sync_token: str | None = None,
        page_token: str | None = None,
    ) -> CalendarEventsResponse:
        """Fetch calendar events with optional sync token for incremental sync."""
        params: dict = {
            "singleEvents": "true",
            "maxResults": "250",
            "orderBy": "startTime",
        }
        if sync_token:
            params["syncToken"] = sync_token
        else:
            if time_min:
                params["timeMin"] = time_min.isoformat() + "Z"
            if time_max:
                params["timeMax"] = time_max.isoformat() + "Z"

        if page_token:
            params["pageToken"] = page_token

        response = await self._request(
            "GET",
            CALENDAR_EVENTS_URL,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code == 410:
            raise SyncTokenInvalidError()

        if response.status_code == 401:
            raise ExternalAPIError(
                status_code=401,
                detail="Calendar access token expired",
                provider="GoogleCalendar",
            )

        if response.status_code != 200:
            raise ExternalAPIError(
                status_code=response.status_code,
                detail="Failed to list calendar events",
                provider="GoogleCalendar",
            )

        data = response.json()
        events = []
        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            organizer = item.get("organizer", {})
            attendee_emails = [
                a.get("email", "")
                for a in item.get("attendees", [])
                if a.get("email")
            ]
            events.append(
                CalendarEvent(
                    event_id=item.get("id", ""),
                    summary=item.get("summary", ""),
                    start_time=start.get("dateTime") or start.get("date"),
                    end_time=end.get("dateTime") or end.get("date"),
                    organizer_email=organizer.get("email"),
                    attendees=attendee_emails,
                    location=item.get("location"),
                    status=item.get("status", "confirmed"),
                )
            )

        return CalendarEventsResponse(
            events=events,
            next_page_token=data.get("nextPageToken"),
            next_sync_token=data.get("nextSyncToken"),
        )

    async def revoke_token(self, token: str) -> bool:
        """Revoke an OAuth token at Google. Returns True on success."""
        logger.info("calendar_revoking_token", oauth_token="[ENCRYPTED]")
        try:
            response = await self._request(
                "POST",
                GOOGLE_REVOKE_URL,
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return response.status_code == 200
        except ExternalAPIError:
            logger.warning("calendar_revoke_failed_gracefully")
            return False
