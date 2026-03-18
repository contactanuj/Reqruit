"""
Calendar event parser for interview detection.

Matches calendar event titles and attendee domains against tracked companies
to detect interview-related events. Non-matching events are silently discarded
and never stored or logged with identifying details (privacy preservation).
"""

import re
from datetime import UTC, datetime, timedelta

import structlog
from pydantic import BaseModel

from src.integrations.email_parser import EmailParser
from src.integrations.google_calendar_client import CalendarEvent

logger = structlog.get_logger()

INTERVIEW_KEYWORDS = re.compile(
    r"interview|technical\s+screen|hiring\s+manager|onsite|panel"
    r"|phone\s+screen|recruiter\s+call|final\s+round|coding\s+round",
    re.I,
)


class CalendarSignalMatch(BaseModel):
    """Result of detecting an interview event from a calendar entry."""

    company_name: str
    matched_pattern: str = "calendar_interview"
    event_date: datetime
    confidence: float
    match_source: str  # "title", "organizer", "attendee"


class CalendarEventParser:
    """
    Detect interview events from calendar entries.

    NEVER stores or logs details of non-matching events (privacy preservation).
    """

    def is_interview_event(
        self,
        event: CalendarEvent,
        tracked_companies: list[str],
    ) -> CalendarSignalMatch | None:
        """
        Check if a calendar event is an interview.

        Returns CalendarSignalMatch if detected, None otherwise.
        Non-matching events are silently discarded.
        """
        title_match = bool(INTERVIEW_KEYWORDS.search(event.summary))

        # Check organizer domain against tracked companies
        organizer_company = None
        if event.organizer_email:
            domain = event.organizer_email.split("@")[-1] if "@" in event.organizer_email else ""
            organizer_company = self._match_company(domain, tracked_companies)

        # Check attendee domains against tracked companies
        attendee_company = None
        for attendee in event.attendees:
            if "@" in attendee:
                domain = attendee.split("@")[-1]
                match = self._match_company(domain, tracked_companies)
                if match:
                    attendee_company = match
                    break

        company = organizer_company or attendee_company
        event_date = event.start_time or datetime.now(UTC)

        if title_match and company:
            return CalendarSignalMatch(
                company_name=company,
                event_date=event_date,
                confidence=0.95,
                match_source="organizer" if organizer_company else "attendee",
            )

        if title_match:
            # Title keyword match but no tracked company — extract from organizer
            extracted = ""
            if event.organizer_email and "@" in event.organizer_email:
                domain = event.organizer_email.split("@")[-1]
                extracted = EmailParser.extract_company_name(domain)
            return CalendarSignalMatch(
                company_name=extracted,
                event_date=event_date,
                confidence=0.7,
                match_source="title",
            )

        if company:
            # Company domain in attendees only — no keyword
            return CalendarSignalMatch(
                company_name=company,
                event_date=event_date,
                confidence=0.6,
                match_source="attendee",
            )

        return None

    @staticmethod
    def _match_company(domain: str, tracked_companies: list[str]) -> str | None:
        """Match a domain against tracked company names."""
        domain_lower = domain.lower()
        company_name = EmailParser.extract_company_name(domain_lower)
        for tracked in tracked_companies:
            if tracked.lower() == company_name.lower():
                return tracked
            if tracked.lower() in domain_lower:
                return tracked
        return None

    @staticmethod
    def is_nudge_eligible(event_date: datetime, days_threshold: int = 3) -> bool:
        """Check if an event is far enough in the future for a prep nudge."""
        now = datetime.now(UTC)
        return event_date > now + timedelta(days=days_threshold)
