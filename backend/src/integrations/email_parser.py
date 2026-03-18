"""
Pattern-based email signal parser for job-related email detection.

Operates EXCLUSIVELY on email metadata (subject, sender domain). NEVER accesses
or stores email body content (NFR-6.9). Patterns are defined in a registry for
easy extension without changing parser logic.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class SignalPattern:
    """A named pattern for detecting job-related email signals."""

    name: str
    subject_patterns: list[re.Pattern] = field(default_factory=list)
    sender_domain_patterns: list[re.Pattern] = field(default_factory=list)
    status_transition: str = ""


# ── Pattern registry ──────────────────────────────────────────────────

SIGNAL_PATTERNS: list[SignalPattern] = [
    SignalPattern(
        name="interview_invitation",
        subject_patterns=[
            re.compile(r"interview\s+(scheduled|invitation|confirmed|request)", re.I),
            re.compile(r"meet\s+the\s+team", re.I),
            re.compile(r"technical\s+round", re.I),
            re.compile(r"phone\s+screen", re.I),
        ],
        status_transition="interviewing",
    ),
    SignalPattern(
        name="rejection",
        subject_patterns=[
            re.compile(r"unfortunately", re.I),
            re.compile(r"not\s+moving\s+forward", re.I),
            re.compile(r"other\s+candidates", re.I),
            re.compile(r"position\s+(has\s+been\s+)?filled", re.I),
            re.compile(r"will\s+not\s+be\s+proceeding", re.I),
        ],
        status_transition="rejected",
    ),
    SignalPattern(
        name="offer",
        subject_patterns=[
            re.compile(r"offer\s+letter", re.I),
            re.compile(r"congratulations", re.I),
            re.compile(r"compensation\s+package", re.I),
            re.compile(r"offer\s+details", re.I),
        ],
        status_transition="offer_received",
    ),
    SignalPattern(
        name="application_confirmation",
        subject_patterns=[
            re.compile(r"application\s+received", re.I),
            re.compile(r"thank\s+you\s+for\s+applying", re.I),
            re.compile(r"application\s+submitted", re.I),
        ],
        status_transition="applied",
    ),
    SignalPattern(
        name="assessment_request",
        subject_patterns=[
            re.compile(r"(coding|technical)\s+(assessment|challenge)", re.I),
            re.compile(r"take[- ]home", re.I),
            re.compile(r"online\s+test", re.I),
        ],
        status_transition="interviewing",
    ),
]


# ── Common non-job sender domains to exclude ──────────────────────────

_NON_JOB_DOMAINS = {
    "amazon.com",  # product orders, not job-related
    "ebay.com",
    "paypal.com",
    "netflix.com",
    "spotify.com",
}

# ── Parser ────────────────────────────────────────────────────────────


@dataclass
class ParsedSignal:
    """Result of parsing an email for job-related signals."""

    matched_pattern: str
    company_name: str
    confidence: float
    event_date: datetime | None = None
    status_transition: str = ""


class EmailParser:
    """
    Parse email metadata (subject + sender) for job-related signals.

    NEVER accesses email body content (NFR-6.9).
    """

    def __init__(self, patterns: list[SignalPattern] | None = None) -> None:
        self._patterns = patterns or SIGNAL_PATTERNS

    def parse_email(
        self,
        subject: str,
        sender_domain: str,
        sender_email: str = "",
    ) -> ParsedSignal | None:
        """
        Match an email against known job-related patterns.

        Returns the highest-confidence match or None if no pattern matches.
        Only uses subject and sender metadata — never email body.
        """
        if sender_domain.lower() in _NON_JOB_DOMAINS:
            return None

        best_match: ParsedSignal | None = None
        best_confidence = 0.0

        for pattern in self._patterns:
            confidence = self._match_pattern(subject, sender_domain, pattern)
            if confidence > best_confidence:
                best_confidence = confidence
                company_name = self.extract_company_name(sender_domain)
                event_date = self.extract_event_date(subject)
                best_match = ParsedSignal(
                    matched_pattern=pattern.name,
                    company_name=company_name,
                    confidence=confidence,
                    event_date=event_date,
                    status_transition=pattern.status_transition,
                )

        return best_match

    @staticmethod
    def _match_pattern(
        subject: str,
        sender_domain: str,
        pattern: SignalPattern,
    ) -> float:
        """Return confidence score for a pattern match. 0.0 = no match."""
        # Check subject patterns
        for regex in pattern.subject_patterns:
            if regex.search(subject):
                return 0.9  # exact subject match

        # Check sender domain patterns
        for regex in pattern.sender_domain_patterns:
            if regex.search(sender_domain):
                return 0.5  # domain-only match

        return 0.0

    @staticmethod
    def extract_company_name(sender_domain: str) -> str:
        """
        Extract company name from sender domain.

        Strips common email subdomains (careers, noreply, hr, recruiting)
        and extracts the main company name.
        """
        domain = sender_domain.lower().strip()
        # Remove common subdomains
        for prefix in ("careers.", "noreply.", "hr.", "recruiting.", "talent.", "jobs."):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]

        # Handle .jobs TLD (e.g., "amazon.jobs" → "Amazon")
        if domain.endswith(".jobs"):
            domain = domain[: -len(".jobs")]

        # Extract company name from remaining domain (before first dot)
        parts = domain.split(".")
        if parts:
            return parts[0].capitalize()
        return domain.capitalize()

    @staticmethod
    def extract_event_date(subject: str) -> datetime | None:
        """
        Extract a date from an email subject line if present.

        Handles common formats: "March 15, 2026", "3/15/2026", "3/15".
        Returns None if no date found.
        """
        # Try "Month Day, Year" format
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        month_pattern = re.compile(
            r"(" + "|".join(month_names.keys()) + r")\s+(\d{1,2})(?:,?\s*(\d{4}))?",
            re.I,
        )
        match = month_pattern.search(subject)
        if match:
            month = month_names[match.group(1).lower()]
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now().year
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        # Try M/D/YYYY or M/D format
        slash_pattern = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?")
        match = slash_pattern.search(subject)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now().year
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        return None
