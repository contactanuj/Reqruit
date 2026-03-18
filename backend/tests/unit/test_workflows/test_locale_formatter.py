"""
Tests for the locale formatting rules module.

Verifies LocaleFormattingRules derivation from MarketConfig conventions
and LLM prompt instruction generation for IN and US markets.
"""

from src.db.documents.market_config import ResumeConventions
from src.workflows.formatters.locale_formatter import (
    IN_DEFAULTS,
    US_DEFAULTS,
    LocaleFormattingRules,
    format_resume_instructions,
    get_formatting_rules,
)


# ---------------------------------------------------------------------------
# get_formatting_rules
# ---------------------------------------------------------------------------


class TestGetFormattingRules:
    def test_india_defaults(self) -> None:
        rules = get_formatting_rules("IN")
        assert rules.paper_size == "A4"
        assert rules.pages_min == 2
        assert rules.pages_max == 3
        assert rules.include_declaration is True
        assert rules.include_ctc is True
        assert rules.include_dob is True
        assert rules.include_photo is False
        assert rules.skills_first is False
        assert rules.format_name == "IN"

    def test_us_defaults(self) -> None:
        rules = get_formatting_rules("US")
        assert rules.paper_size == "letter"
        assert rules.pages_min == 1
        assert rules.pages_max == 1
        assert rules.include_declaration is False
        assert rules.include_ctc is False
        assert rules.include_dob is False
        assert rules.include_photo is False
        assert rules.skills_first is True
        assert rules.format_name == "US"

    def test_unknown_region_defaults_to_us(self) -> None:
        rules = get_formatting_rules("XX")
        assert rules.format_name == "US"
        assert rules.paper_size == "letter"

    def test_from_conventions(self) -> None:
        conventions = ResumeConventions(
            include_photo=False,
            include_dob=True,
            include_declaration=True,
            expected_pages_min=2,
            expected_pages_max=3,
            paper_size="A4",
            expected_salary_field=True,
        )
        rules = get_formatting_rules("IN", conventions)
        assert rules.include_dob is True
        assert rules.include_declaration is True
        assert rules.pages_max == 3
        assert rules.paper_size == "A4"
        assert rules.include_ctc is True

    def test_us_conventions_set_skills_first(self) -> None:
        conventions = ResumeConventions(
            include_photo=False,
            include_dob=False,
            include_declaration=False,
            expected_pages_min=1,
            expected_pages_max=1,
            paper_size="letter",
            expected_salary_field=False,
        )
        rules = get_formatting_rules("US", conventions)
        assert rules.skills_first is True

    def test_in_conventions_no_skills_first(self) -> None:
        conventions = ResumeConventions(
            include_photo=False,
            include_dob=True,
            include_declaration=True,
            expected_pages_min=2,
            expected_pages_max=3,
            paper_size="A4",
            expected_salary_field=True,
        )
        rules = get_formatting_rules("IN", conventions)
        assert rules.skills_first is False


# ---------------------------------------------------------------------------
# format_resume_instructions
# ---------------------------------------------------------------------------


class TestFormatResumeInstructions:
    def test_india_instructions(self) -> None:
        instructions = format_resume_instructions(IN_DEFAULTS)
        assert "FORMAT FOR IN MARKET" in instructions
        assert "A4" in instructions
        assert "2-3 pages" in instructions
        assert "declaration" in instructions.lower()
        assert "CTC" in instructions
        assert "date of birth" in instructions.lower()

    def test_us_instructions(self) -> None:
        instructions = format_resume_instructions(US_DEFAULTS)
        assert "FORMAT FOR US MARKET" in instructions
        assert "letter" in instructions.lower()
        assert "1-1 pages" in instructions
        assert "skills" in instructions.lower()
        assert "Do NOT include" in instructions

    def test_us_no_declaration_or_dob(self) -> None:
        instructions = format_resume_instructions(US_DEFAULTS)
        assert "Do NOT include a declaration section" in instructions
        assert "Do NOT include salary/CTC expectations" in instructions
        assert "Do NOT include date of birth" in instructions
