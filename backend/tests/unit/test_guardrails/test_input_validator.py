"""Unit tests for src/guardrails/input_validator.py."""

from unittest.mock import AsyncMock, patch

from src.guardrails.input_validator import (
    InputType,
    ValidationResult,
    validate_file_upload,
    validate_text,
    validate_text_with_llm,
)


class TestValidateText:
    # -- FREE_TEXT --

    def test_clean_free_text_passes(self):
        result = validate_text("I want to apply for the senior engineer role", InputType.FREE_TEXT)
        assert result.is_valid is True
        assert result.violations == []

    def test_free_text_too_long_fails(self):
        text = "x" * 10_001
        result = validate_text(text, InputType.FREE_TEXT)
        assert result.is_valid is False
        assert any("exceeds maximum length" in v for v in result.violations)

    def test_free_text_exactly_at_limit_passes(self):
        text = "x" * 10_000
        result = validate_text(text, InputType.FREE_TEXT)
        assert result.is_valid is True

    def test_free_text_with_ssn_fails(self):
        result = validate_text("My SSN is 123-45-6789", InputType.FREE_TEXT)
        assert result.is_valid is False
        assert any("ssn" in v.lower() for v in result.violations)

    def test_free_text_with_credit_card_fails(self):
        result = validate_text("Card number: 4111111111111111", InputType.FREE_TEXT)
        assert result.is_valid is False
        assert any("credit_card" in v.lower() for v in result.violations)

    def test_free_text_with_email_passes(self):
        """Emails are common in cover letters — should not be blocked."""
        result = validate_text("Reach me at dev@example.com", InputType.FREE_TEXT)
        assert result.is_valid is True

    # -- PROFILE_FIELD --

    def test_clean_profile_field_passes(self):
        result = validate_text("Software Engineer", InputType.PROFILE_FIELD)
        assert result.is_valid is True

    def test_profile_field_too_long_fails(self):
        text = "y" * 2_001
        result = validate_text(text, InputType.PROFILE_FIELD)
        assert result.is_valid is False

    # -- JOB_URL --

    def test_valid_https_url_passes(self):
        result = validate_text("https://jobs.example.com/posting/123", InputType.JOB_URL)
        assert result.is_valid is True

    def test_valid_http_url_passes(self):
        result = validate_text("http://jobs.example.com/posting/123", InputType.JOB_URL)
        assert result.is_valid is True

    def test_url_without_scheme_fails(self):
        result = validate_text("jobs.example.com/posting/123", InputType.JOB_URL)
        assert result.is_valid is False
        assert any("HTTP or HTTPS" in v for v in result.violations)

    def test_url_too_long_fails(self):
        url = "https://example.com/" + "a" * 2_040
        result = validate_text(url, InputType.JOB_URL)
        assert result.is_valid is False

    # -- ValidationResult helpers --

    def test_first_violation_returns_first_message(self):
        result = ValidationResult(is_valid=False, violations=["error1", "error2"])
        assert result.first_violation == "error1"

    def test_first_violation_none_when_valid(self):
        result = ValidationResult(is_valid=True)
        assert result.first_violation is None


class TestValidateFileUpload:
    def test_valid_pdf_passes(self):
        result = validate_file_upload(
            filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=1024 * 500,  # 500 KB
        )
        assert result.is_valid is True

    def test_valid_docx_passes(self):
        result = validate_file_upload(
            filename="resume.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=1024 * 200,
        )
        assert result.is_valid is True

    def test_wrong_extension_fails(self):
        result = validate_file_upload(
            filename="resume.txt",
            content_type="text/plain",
            size_bytes=1024,
        )
        assert result.is_valid is False
        assert any("not allowed" in v for v in result.violations)

    def test_wrong_content_type_fails(self):
        result = validate_file_upload(
            filename="resume.pdf",
            content_type="text/html",
            size_bytes=1024,
        )
        assert result.is_valid is False

    def test_file_too_large_fails(self):
        result = validate_file_upload(
            filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=11 * 1024 * 1024,  # 11 MB
        )
        assert result.is_valid is False
        assert any("exceeds" in v for v in result.violations)

    def test_exactly_at_size_limit_passes(self):
        result = validate_file_upload(
            filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=10 * 1024 * 1024,  # exactly 10 MB
        )
        assert result.is_valid is True


class TestValidateTextWithLlm:
    async def test_clean_text_passes_without_llm_call_when_no_api_key(self):
        """If no API key is configured, LLM moderation is skipped and text passes."""
        result = await validate_text_with_llm(
            "I am excited to apply for this position",
            InputType.FREE_TEXT,
        )
        assert result.is_valid is True

    async def test_rule_violation_returns_before_llm_call(self):
        """Rule violations short-circuit before LLM moderation is attempted."""
        text = "x" * 10_001
        with patch(
            "src.guardrails.input_validator._openai_moderation",
            new_callable=AsyncMock,
        ) as mock_mod:
            result = await validate_text_with_llm(text, InputType.FREE_TEXT)
            assert result.is_valid is False
            mock_mod.assert_not_called()

    async def test_non_free_text_skips_llm_moderation(self):
        """PROFILE_FIELD inputs do not trigger LLM moderation."""
        with patch(
            "src.guardrails.input_validator._openai_moderation",
            new_callable=AsyncMock,
        ) as mock_mod:
            result = await validate_text_with_llm("Software Engineer", InputType.PROFILE_FIELD)
            assert result.is_valid is True
            mock_mod.assert_not_called()

    async def test_llm_flagged_content_fails(self):
        """If OpenAI moderation flags content, validation fails."""
        with patch(
            "src.guardrails.input_validator._openai_moderation",
            new_callable=AsyncMock,
            return_value=ValidationResult(
                is_valid=False,
                violations=["Content flagged: harassment"],
            ),
        ):
            result = await validate_text_with_llm(
                "some flagged text",
                InputType.FREE_TEXT,
            )
            assert result.is_valid is False
            assert any("flagged" in v for v in result.violations)

    async def test_llm_error_fails_open(self):
        """If LLM moderation raises an exception, text is considered valid (fail open)."""
        with patch(
            "src.guardrails.input_validator._openai_moderation",
            new_callable=AsyncMock,
            return_value=ValidationResult(is_valid=True),
        ):
            result = await validate_text_with_llm(
                "clean text",
                InputType.FREE_TEXT,
            )
            assert result.is_valid is True
