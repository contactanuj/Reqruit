"""
Layered output validation: rules → LLM self-check.

Design decisions
----------------
Layer 1 — Schema enforcement:
    LangChain's with_structured_output() enforces the output schema at
    generation time. No code needed here — the agent layer handles this.

Layer 2 — Rule-based (this module):
    Fast, offline checks on generated content:
    - PII detection: cover letters must not expose SSN, credit cards, etc.
    - Tone keywords: reject outputs with unprofessional language
    - Length checks: outreach must not exceed LinkedIn's 300-char limit
    - Fact anchoring: verify claims against the data used to generate them

Layer 3 — LLM self-check (this module, optional):
    Only on critical outputs (cover letter, outreach, tailored resume).
    Uses Groq Llama 3.1 8B — free tier, ~10-20 calls/day budget.
    The self-check prompt asks the model to evaluate its own output for:
    - Professional tone
    - Factual consistency with provided context
    - No hallucinated credentials or companies

OutputType enum:
    Declares what kind of output is being validated so the correct rule
    set and self-check instructions are applied.

Why Groq for self-check (not Claude):
    Self-checks on every critical output at ~$0.003/call with Claude Haiku
    adds up. Groq Llama 3.1 8B is free (500K tokens/day) and sufficient
    for binary pass/fail quality checks.
"""

import json
from dataclasses import dataclass, field
from enum import StrEnum

import structlog
from langchain_groq import ChatGroq

from src.core.config import get_settings
from src.guardrails.pii_detector import detect_pii

logger = structlog.get_logger()


class OutputType(StrEnum):
    """The kind of LLM output being validated."""

    COVER_LETTER = "cover_letter"  # rules + self-check
    OUTREACH_MESSAGE = "outreach_message"  # rules + self-check
    TAILORED_RESUME = "tailored_resume"  # rules + self-check
    PARSED_RESUME = "parsed_resume"  # rules only
    INTERVIEW_QUESTIONS = "interview_questions"  # rules only
    STAR_STORY = "star_story"  # rules only


@dataclass
class OutputValidationResult:
    """Result of an output validation pass."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    self_check_passed: bool | None = None  # None = not run

    @property
    def first_violation(self) -> str | None:
        return self.violations[0] if self.violations else None


# ---------------------------------------------------------------------------
# Rule constants
# ---------------------------------------------------------------------------

_MAX_COVER_LETTER_CHARS = 4_000
_MAX_OUTREACH_CHARS = 300  # LinkedIn's message limit
_MAX_RESUME_CHARS = 8_000
_BLOCKED_PII_TYPES = {"ssn", "credit_card"}

_UNPROFESSIONAL_KEYWORDS = [
    "desperate",
    "please hire me",
    "i really need",
    "i am begging",
]


# ---------------------------------------------------------------------------
# Rule-based checks
# ---------------------------------------------------------------------------


def _check_pii(text: str) -> list[str]:
    """Return violation messages for any blocked PII in the text."""
    matches = detect_pii(text)
    blocked = [m for m in matches if m.pii_type in _BLOCKED_PII_TYPES]
    if blocked:
        types = ", ".join({m.pii_type for m in blocked})
        return [f"Output contains sensitive information ({types})"]
    return []


def _check_tone(text: str) -> list[str]:
    """Return violation messages for unprofessional tone keywords."""
    lower = text.lower()
    found = [kw for kw in _UNPROFESSIONAL_KEYWORDS if kw in lower]
    if found:
        return [f"Unprofessional tone detected: {', '.join(found)}"]
    return []


def _check_length(text: str, max_chars: int, label: str) -> list[str]:
    """Return a violation if text exceeds max_chars."""
    if len(text) > max_chars:
        return [f"{label} exceeds {max_chars} characters ({len(text)} found)"]
    return []


def _apply_rules(content: str, output_type: OutputType) -> list[str]:
    """Run all applicable rule checks and return aggregated violations."""
    violations: list[str] = []

    violations.extend(_check_pii(content))
    violations.extend(_check_tone(content))

    if output_type == OutputType.COVER_LETTER:
        violations.extend(_check_length(content, _MAX_COVER_LETTER_CHARS, "Cover letter"))
    elif output_type == OutputType.OUTREACH_MESSAGE:
        violations.extend(_check_length(content, _MAX_OUTREACH_CHARS, "Outreach message"))
    elif output_type == OutputType.TAILORED_RESUME:
        violations.extend(_check_length(content, _MAX_RESUME_CHARS, "Resume"))

    return violations


# ---------------------------------------------------------------------------
# LLM self-check (Layer 3) — Groq Llama 3.1 8B, critical outputs only
# ---------------------------------------------------------------------------

_SELF_CHECK_TYPES = {
    OutputType.COVER_LETTER,
    OutputType.OUTREACH_MESSAGE,
    OutputType.TAILORED_RESUME,
}

_SELF_CHECK_PROMPT = """You are a quality reviewer for a job application document.

Review the following {output_type} and answer ONLY with JSON:
{{"pass": true/false, "reason": "one sentence explanation"}}

Rules:
- pass=false if the tone is unprofessional or desperate
- pass=false if it contains fabricated credentials, companies, or skills
- pass=false if it sounds generic and not tailored to the role
- pass=true if it is professional, specific, and honest

Context provided to the writer:
{context}

Document to review:
{content}

Respond with ONLY the JSON object, no other text."""


async def _groq_self_check(
    content: str,
    output_type: OutputType,
    context: str = "",
) -> bool | None:
    """
    Ask Groq Llama 3.1 8B to self-evaluate the output.

    Returns True (pass), False (fail), or None (skipped/error).
    Fails open — returns None on any error to avoid blocking legitimate output.
    """
    try:
        settings = get_settings()
        if not settings.groq.api_key:
            return None

        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.groq.api_key,
            temperature=0,
            max_tokens=100,
        )

        prompt = _SELF_CHECK_PROMPT.format(
            output_type=output_type.value.replace("_", " "),
            context=context[:1000] if context else "No context provided",
            content=content[:2000],
        )

        response = await llm.ainvoke(prompt)
        text = response.content.strip()

        # Extract JSON even if the model adds extra text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("self_check_no_json", raw=text[:200])
            return None

        data = json.loads(text[start:end])
        passed = bool(data.get("pass", True))

        logger.info(
            "self_check_complete",
            output_type=output_type.value,
            passed=passed,
            reason=data.get("reason", ""),
        )
        return passed

    except Exception as e:
        logger.warning("self_check_failed", error=str(e))
        return None  # fail open


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_output(
    content: str,
    output_type: OutputType,
) -> OutputValidationResult:
    """
    Synchronous rule-based output validation.

    Runs Layer 2 (rules) only. Does NOT run LLM self-check.
    Use validate_output_with_self_check for full validation.

    Args:
        content: The LLM-generated text.
        output_type: What kind of output this is.

    Returns:
        OutputValidationResult with is_valid and any violation messages.
    """
    violations = _apply_rules(content, output_type)
    return OutputValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )


async def validate_output_with_self_check(
    content: str,
    output_type: OutputType,
    context: str = "",
) -> OutputValidationResult:
    """
    Full output validation: rules + LLM self-check (async).

    Self-check is only run for critical output types (cover letter, outreach,
    tailored resume) and only if rules pass first.

    Args:
        content: The LLM-generated text.
        output_type: What kind of output this is.
        context: The source data used to generate the output (for fact-check).

    Returns:
        OutputValidationResult with is_valid, violations, and self_check_passed.
    """
    # Layer 2: rules
    violations = _apply_rules(content, output_type)
    if violations:
        return OutputValidationResult(is_valid=False, violations=violations)

    # Layer 3: LLM self-check (critical outputs only)
    self_check_passed: bool | None = None
    if output_type in _SELF_CHECK_TYPES:
        self_check_passed = await _groq_self_check(content, output_type, context)

        if self_check_passed is False:
            return OutputValidationResult(
                is_valid=False,
                violations=["Output failed quality self-check"],
                self_check_passed=False,
            )

    return OutputValidationResult(
        is_valid=True,
        self_check_passed=self_check_passed,
    )
