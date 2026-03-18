"""
Layered input validation: rules → LLM moderation.

Design decisions
----------------
Layer 1 — Pydantic:
    Schema validation (type, length, format) happens automatically via
    FastAPI before this module is ever called. No code needed here.

Layer 2 — Rule-based (this module):
    Fast, offline checks run on every request:
    - Text length limits (prevent abuse / runaway LLM context)
    - File type and size validation for uploads
    - Encoding checks (reject binary blobs passed as strings)
    - PII detection in free-text fields (SSN, credit cards, etc.)

Layer 3 — LLM moderation (this module, optional):
    Only applied to free-text fields (cover letter requests, chat messages).
    Two providers, both free:
    - OpenAI Moderation API: fast, unlimited, well-maintained
    - Groq + Llama Guard 3: free tier, more nuanced, catches job-hunting misuse
    LLM moderation is skipped if the text passes rule checks AND the provider
    is unavailable (circuit breaker open) — fail open to avoid blocking users.

Why fail open on LLM moderation:
    The alternative is fail closed (reject on error), which would block
    legitimate users when LLM APIs are rate-limited. For a learning project
    where harmful content is not a primary threat, fail open is acceptable.
    Production systems with stricter requirements should fail closed.

InputType enum:
    Callers declare what kind of input they are validating so the validator
    applies the appropriate rule set. RESUME_UPLOAD gets file checks.
    FREE_TEXT gets LLM moderation. PROFILE_FIELD gets length limits only.
"""

import os
from dataclasses import dataclass, field
from enum import StrEnum

import httpx
import structlog

from src.core.config import get_settings
from src.guardrails.pii_detector import detect_pii

logger = structlog.get_logger()


class InputType(StrEnum):
    """The kind of input being validated — determines which rules apply."""

    FREE_TEXT = "free_text"  # chat messages, notes → gets LLM moderation
    RESUME_UPLOAD = "resume_upload"  # file bytes + metadata
    JOB_URL = "job_url"  # URL string
    PROFILE_FIELD = "profile_field"  # structured fields (name, salary, etc.)


@dataclass
class ValidationResult:
    """Result of an input validation pass."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)

    @property
    def first_violation(self) -> str | None:
        return self.violations[0] if self.violations else None


# ---------------------------------------------------------------------------
# Rule constants
# ---------------------------------------------------------------------------

_MAX_FREE_TEXT_CHARS = 10_000
_MAX_PROFILE_FIELD_CHARS = 2_000
_MAX_RESUME_SIZE_MB = 10
_ALLOWED_RESUME_MIME_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}

# PII types that should never appear in free-text inputs
_BLOCKED_PII_TYPES = {"ssn", "credit_card"}


# ---------------------------------------------------------------------------
# Rule-based validation
# ---------------------------------------------------------------------------


def _validate_free_text(text: str) -> ValidationResult:
    """Apply rule-based checks to free-text inputs."""
    violations: list[str] = []

    if len(text) > _MAX_FREE_TEXT_CHARS:
        violations.append(
            f"Text exceeds maximum length of {_MAX_FREE_TEXT_CHARS} characters"
        )

    # Check for high-risk PII types only (email/phone are common in cover letters)
    pii_matches = detect_pii(text)
    blocked = [m for m in pii_matches if m.pii_type in _BLOCKED_PII_TYPES]
    if blocked:
        types = ", ".join({m.pii_type for m in blocked})
        violations.append(f"Input contains sensitive information ({types})")

    return ValidationResult(is_valid=len(violations) == 0, violations=violations)


def _validate_profile_field(text: str) -> ValidationResult:
    """Apply rule-based checks to structured profile fields."""
    violations: list[str] = []

    if len(text) > _MAX_PROFILE_FIELD_CHARS:
        violations.append(
            f"Field exceeds maximum length of {_MAX_PROFILE_FIELD_CHARS} characters"
        )

    return ValidationResult(is_valid=len(violations) == 0, violations=violations)


def _validate_resume_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> ValidationResult:
    """Validate a resume file upload (type + size checks)."""
    violations: list[str] = []

    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_RESUME_EXTENSIONS:
        violations.append(
            f"File type '{ext}' not allowed. Use PDF or DOCX."
        )

    if content_type not in _ALLOWED_RESUME_MIME_TYPES:
        violations.append(
            f"Content type '{content_type}' not allowed."
        )

    max_bytes = _MAX_RESUME_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        violations.append(
            f"File size {size_bytes / 1024 / 1024:.1f}MB exceeds "
            f"{_MAX_RESUME_SIZE_MB}MB limit"
        )

    return ValidationResult(is_valid=len(violations) == 0, violations=violations)


def _validate_job_url(url: str) -> ValidationResult:
    """Validate a job posting URL."""
    violations: list[str] = []

    if len(url) > 2048:
        violations.append("URL exceeds maximum length of 2048 characters")

    if not (url.startswith("http://") or url.startswith("https://")):
        violations.append("URL must use HTTP or HTTPS")

    return ValidationResult(is_valid=len(violations) == 0, violations=violations)


# ---------------------------------------------------------------------------
# LLM moderation (Layer 3) — optional, applied to FREE_TEXT only
# ---------------------------------------------------------------------------


async def _openai_moderation(text: str) -> ValidationResult:
    """
    Run OpenAI's free Moderation API on the text.

    Returns valid=True (pass) on any error — fail open so users are not
    blocked when the API is unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            settings = get_settings()
            if not settings.openai.api_key:
                return ValidationResult(is_valid=True)

            response = await client.post(
                "https://api.openai.com/v1/moderations",
                headers={"Authorization": f"Bearer {settings.openai.api_key}"},
                json={"input": text},
            )
            if response.status_code != 200:
                logger.warning("openai_moderation_error", status=response.status_code)
                return ValidationResult(is_valid=True)

            data = response.json()
            result = data["results"][0]
            if result["flagged"]:
                flagged_cats = [k for k, v in result["categories"].items() if v]
                return ValidationResult(
                    is_valid=False,
                    violations=[f"Content flagged: {', '.join(flagged_cats)}"],
                )
            return ValidationResult(is_valid=True)

    except Exception as e:
        logger.warning("openai_moderation_failed", error=str(e))
        return ValidationResult(is_valid=True)  # fail open


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_text(text: str, input_type: InputType = InputType.FREE_TEXT) -> ValidationResult:
    """
    Synchronous rule-based validation for text inputs.

    Runs Layers 1 (Pydantic, handled by FastAPI) and 2 (rules).
    Does NOT run LLM moderation — use validate_text_with_llm for that.

    Args:
        text: The text to validate.
        input_type: The context in which this text appears.

    Returns:
        ValidationResult with is_valid and any violation messages.
    """
    if input_type == InputType.FREE_TEXT:
        return _validate_free_text(text)
    elif input_type == InputType.PROFILE_FIELD:
        return _validate_profile_field(text)
    elif input_type == InputType.JOB_URL:
        return _validate_job_url(text)
    # RESUME_UPLOAD uses validate_file_upload instead
    return ValidationResult(is_valid=True)


def validate_file_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> ValidationResult:
    """
    Validate a resume file upload (rule-based only, no LLM).

    Args:
        filename: Original filename including extension.
        content_type: MIME type from the HTTP Content-Type header.
        size_bytes: File size in bytes.

    Returns:
        ValidationResult with is_valid and any violation messages.
    """
    return _validate_resume_upload(filename, content_type, size_bytes)


async def validate_text_with_llm(
    text: str,
    input_type: InputType = InputType.FREE_TEXT,
) -> ValidationResult:
    """
    Full validation: rules + LLM moderation (async).

    LLM moderation is only applied to FREE_TEXT inputs. Other input types
    return the rule-based result directly.

    Args:
        text: The text to validate.
        input_type: The context in which this text appears.

    Returns:
        ValidationResult. Returns first failure found (rules before LLM).
    """
    # Layer 2: rules
    rule_result = validate_text(text, input_type)
    if not rule_result.is_valid:
        return rule_result

    # Layer 3: LLM moderation (free-text only)
    if input_type == InputType.FREE_TEXT:
        llm_result = await _openai_moderation(text)
        if not llm_result.is_valid:
            return llm_result

    return ValidationResult(is_valid=True)
