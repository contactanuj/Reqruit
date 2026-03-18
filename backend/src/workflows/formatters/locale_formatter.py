"""
Locale-aware formatting rules for application assembly.

Converts MarketConfig.ResumeConventions into structured formatting rules
and LLM prompt instructions. Pure Python — no LLM calls.
"""

from dataclasses import dataclass

from src.db.documents.market_config import ResumeConventions


@dataclass
class LocaleFormattingRules:
    """Structured formatting rules derived from market conventions."""

    paper_size: str
    pages_min: int
    pages_max: int
    include_declaration: bool
    include_ctc: bool
    include_dob: bool
    include_photo: bool
    skills_first: bool
    format_name: str


US_DEFAULTS = LocaleFormattingRules(
    paper_size="letter",
    pages_min=1,
    pages_max=1,
    include_declaration=False,
    include_ctc=False,
    include_dob=False,
    include_photo=False,
    skills_first=True,
    format_name="US",
)

IN_DEFAULTS = LocaleFormattingRules(
    paper_size="A4",
    pages_min=2,
    pages_max=3,
    include_declaration=True,
    include_ctc=True,
    include_dob=True,
    include_photo=False,
    skills_first=False,
    format_name="IN",
)

_DEFAULTS = {"US": US_DEFAULTS, "IN": IN_DEFAULTS}


def get_formatting_rules(
    region_code: str, conventions: ResumeConventions | None = None
) -> LocaleFormattingRules:
    """Derive formatting rules from MarketConfig conventions or fallback defaults."""
    if conventions:
        return LocaleFormattingRules(
            paper_size=conventions.paper_size,
            pages_min=conventions.expected_pages_min,
            pages_max=conventions.expected_pages_max,
            include_declaration=conventions.include_declaration,
            include_ctc=conventions.expected_salary_field,
            include_dob=conventions.include_dob,
            include_photo=conventions.include_photo,
            skills_first=(region_code == "US"),
            format_name=region_code,
        )
    return _DEFAULTS.get(region_code, US_DEFAULTS)


def format_resume_instructions(rules: LocaleFormattingRules) -> str:
    """Convert formatting rules to LLM prompt instructions."""
    lines = [f"FORMAT FOR {rules.format_name} MARKET:"]
    lines.append(f"- Paper size: {rules.paper_size}")
    lines.append(f"- Target length: {rules.pages_min}-{rules.pages_max} pages")

    if rules.include_declaration:
        lines.append("- Include a declaration section at the end")
    if rules.include_ctc:
        lines.append("- Include expected CTC / salary expectations field")
    if rules.include_dob:
        lines.append("- Include date of birth")
    if rules.include_photo:
        lines.append("- Include photo placeholder")
    if rules.skills_first:
        lines.append("- Lead with skills/technical summary section")

    if not rules.include_declaration:
        lines.append("- Do NOT include a declaration section")
    if not rules.include_ctc:
        lines.append("- Do NOT include salary/CTC expectations")
    if not rules.include_dob:
        lines.append("- Do NOT include date of birth or personal details")

    return "\n".join(lines)
