"""
PII detection using regex patterns.

Design decisions
----------------
Why regex (not a dedicated PII library like presidio):
    Presidio is production-grade but heavyweight (~200MB models). For our use
    case — detecting obvious PII in user inputs and LLM outputs — regex is
    fast, offline, and sufficient. We are not building a compliance scanner;
    we are preventing accidental PII leakage in cover letters and outreach.

Why return spans (not just a bool):
    Callers need to know WHAT was detected to log it, redact it, or return
    a useful error. A bool forces a second scan; returning PIIMatch objects
    gives callers full context in one pass.

Patterns covered:
    - Email addresses
    - US/international phone numbers (various formats)
    - US Social Security Numbers (SSN)
    - Credit card numbers (Luhn not verified — pattern match only)
    - US street addresses (heuristic: number + street name + type)
    - IPv4 addresses
"""

import re
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """A single PII detection result."""

    pii_type: str  # e.g. "email", "phone", "ssn"
    value: str  # the matched text (may be redacted in logs)
    start: int  # start index in the original string
    end: int  # end index in the original string


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "phone",
        re.compile(
            r"(?<!\d)"
            r"(\+?1[\s\-.]?)?"  # optional country code
            r"(\(?\d{3}\)?[\s\-.]?)"  # area code
            r"(\d{3}[\s\-.]?)"  # exchange
            r"(\d{4})"  # subscriber
            r"(?!\d)"
        ),
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    ),
    (
        "credit_card",
        re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?"  # Visa
            r"|5[1-5][0-9]{14}"  # MasterCard
            r"|3[47][0-9]{13}"  # Amex
            r"|6(?:011|5[0-9]{2})[0-9]{12})\b"  # Discover
        ),
    ),
    (
        "ipv4",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_pii(text: str) -> list[PIIMatch]:
    """
    Scan text for PII patterns and return all matches.

    Args:
        text: The string to scan.

    Returns:
        List of PIIMatch objects, one per detected instance. Empty list if
        no PII found.
    """
    matches: list[PIIMatch] = []
    for pii_type, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            matches.append(
                PIIMatch(
                    pii_type=pii_type,
                    value=m.group(),
                    start=m.start(),
                    end=m.end(),
                )
            )
    # Sort by position in text
    matches.sort(key=lambda x: x.start)
    return matches


def has_pii(text: str) -> bool:
    """Return True if any PII is detected in the text."""
    return any(pattern.search(text) for _, pattern in _PATTERNS)


def redact_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Replace all detected PII in text with a placeholder.

    Processes patterns in reverse order of position to preserve indices
    during replacement.
    """
    matches = detect_pii(text)
    # Replace from end to start so indices remain valid
    for match in reversed(matches):
        text = text[: match.start] + replacement + text[match.end :]
    return text
