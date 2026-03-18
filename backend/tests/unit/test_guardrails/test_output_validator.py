"""Unit tests for src/guardrails/output_validator.py."""

from unittest.mock import AsyncMock, patch

from src.guardrails.output_validator import (
    OutputType,
    OutputValidationResult,
    validate_output,
    validate_output_with_self_check,
)


class TestValidateOutput:
    # -- Cover letter rules --

    def test_clean_cover_letter_passes(self):
        text = "Dear Hiring Manager, I am excited to apply for the Software Engineer role."
        result = validate_output(text, OutputType.COVER_LETTER)
        assert result.is_valid is True

    def test_cover_letter_with_ssn_fails(self):
        text = "My SSN is 123-45-6789. I am applying for the role."
        result = validate_output(text, OutputType.COVER_LETTER)
        assert result.is_valid is False
        assert any("ssn" in v.lower() for v in result.violations)

    def test_cover_letter_with_credit_card_fails(self):
        text = "Card: 4111111111111111. Please see my attached resume."
        result = validate_output(text, OutputType.COVER_LETTER)
        assert result.is_valid is False

    def test_cover_letter_too_long_fails(self):
        text = "x" * 4_001
        result = validate_output(text, OutputType.COVER_LETTER)
        assert result.is_valid is False
        assert any("exceeds" in v for v in result.violations)

    def test_cover_letter_at_length_limit_passes(self):
        text = "a" * 4_000
        result = validate_output(text, OutputType.COVER_LETTER)
        # May fail tone check but not length
        length_violations = [v for v in result.violations if "exceeds" in v]
        assert len(length_violations) == 0

    def test_unprofessional_tone_fails(self):
        text = "I am desperate for this job. Please hire me."
        result = validate_output(text, OutputType.COVER_LETTER)
        assert result.is_valid is False
        assert any("tone" in v.lower() for v in result.violations)

    # -- Outreach message rules --

    def test_clean_outreach_passes(self):
        text = "Hi Jane, I noticed your work at Acme Corp. I would love to connect."
        result = validate_output(text, OutputType.OUTREACH_MESSAGE)
        assert result.is_valid is True

    def test_outreach_too_long_fails(self):
        text = "x" * 301
        result = validate_output(text, OutputType.OUTREACH_MESSAGE)
        assert result.is_valid is False
        assert any("Outreach message" in v for v in result.violations)

    def test_outreach_at_limit_passes(self):
        text = "x" * 300
        result = validate_output(text, OutputType.OUTREACH_MESSAGE)
        assert result.is_valid is True

    # -- Parsed resume (rules only, no length check) --

    def test_parsed_resume_passes(self):
        result = validate_output("5 years Python experience", OutputType.PARSED_RESUME)
        assert result.is_valid is True

    # -- OutputValidationResult helpers --

    def test_first_violation_returns_first(self):
        result = OutputValidationResult(is_valid=False, violations=["v1", "v2"])
        assert result.first_violation == "v1"

    def test_first_violation_none_when_valid(self):
        result = OutputValidationResult(is_valid=True)
        assert result.first_violation is None

    def test_self_check_passed_none_by_default(self):
        result = OutputValidationResult(is_valid=True)
        assert result.self_check_passed is None


class TestValidateOutputWithSelfCheck:
    async def test_rule_violation_skips_self_check(self):
        """Rule violations short-circuit before LLM self-check."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
        ) as mock_check:
            text = "x" * 4_001
            result = await validate_output_with_self_check(text, OutputType.COVER_LETTER)
            assert result.is_valid is False
            mock_check.assert_not_called()

    async def test_self_check_not_run_for_non_critical_types(self):
        """PARSED_RESUME does not trigger self-check."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
        ) as mock_check:
            result = await validate_output_with_self_check(
                "Python 5 years",
                OutputType.PARSED_RESUME,
            )
            assert result.is_valid is True
            assert result.self_check_passed is None
            mock_check.assert_not_called()

    async def test_self_check_run_for_cover_letter(self):
        """Cover letters trigger the self-check."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check:
            text = "Dear Hiring Manager, I am excited to apply."
            result = await validate_output_with_self_check(text, OutputType.COVER_LETTER)
            assert result.is_valid is True
            assert result.self_check_passed is True
            mock_check.assert_called_once()

    async def test_self_check_run_for_outreach(self):
        """Outreach messages trigger the self-check."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check:
            text = "Hi, I would love to connect about opportunities."
            result = await validate_output_with_self_check(text, OutputType.OUTREACH_MESSAGE)
            assert result.is_valid is True
            mock_check.assert_called_once()

    async def test_self_check_fail_returns_invalid(self):
        """If self-check fails, the result is invalid."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
            return_value=False,
        ):
            text = "Dear Hiring Manager, I am excited to apply."
            result = await validate_output_with_self_check(text, OutputType.COVER_LETTER)
            assert result.is_valid is False
            assert result.self_check_passed is False
            assert any("self-check" in v for v in result.violations)

    async def test_self_check_none_fails_open(self):
        """If self-check returns None (error/skipped), the output is considered valid."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
            return_value=None,
        ):
            text = "Dear Hiring Manager, I am excited to apply."
            result = await validate_output_with_self_check(text, OutputType.COVER_LETTER)
            assert result.is_valid is True
            assert result.self_check_passed is None

    async def test_context_passed_to_self_check(self):
        """Context is forwarded to the self-check for fact verification."""
        with patch(
            "src.guardrails.output_validator._groq_self_check",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check:
            text = "Dear Hiring Manager, I am excited to apply."
            context = "Job: Senior Engineer at Acme Corp"
            await validate_output_with_self_check(
                text, OutputType.COVER_LETTER, context=context
            )
            _, kwargs = mock_check.call_args
            # context is passed as positional or keyword arg
            call_args = mock_check.call_args
            assert context in str(call_args)
