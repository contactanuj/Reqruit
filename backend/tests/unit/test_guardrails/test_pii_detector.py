"""Unit tests for src/guardrails/pii_detector.py."""


from src.guardrails.pii_detector import detect_pii, has_pii, redact_pii


class TestDetectPii:
    def test_detects_email(self):
        matches = detect_pii("Contact me at user@example.com please")
        assert any(m.pii_type == "email" for m in matches)

    def test_detects_phone_plain(self):
        matches = detect_pii("Call 555-867-5309 for details")
        assert any(m.pii_type == "phone" for m in matches)

    def test_detects_phone_with_parens(self):
        matches = detect_pii("Reach me at (555) 867-5309")
        assert any(m.pii_type == "phone" for m in matches)

    def test_detects_ssn(self):
        matches = detect_pii("My SSN is 123-45-6789")
        assert any(m.pii_type == "ssn" for m in matches)

    def test_detects_ssn_no_dashes(self):
        matches = detect_pii("SSN 123456789 on file")
        assert any(m.pii_type == "ssn" for m in matches)

    def test_detects_ipv4(self):
        matches = detect_pii("Server at 192.168.1.100")
        assert any(m.pii_type == "ipv4" for m in matches)

    def test_detects_visa_card(self):
        matches = detect_pii("Card: 4111111111111111")
        assert any(m.pii_type == "credit_card" for m in matches)

    def test_no_pii_returns_empty(self):
        matches = detect_pii("I have 5 years of Python experience at Acme Corp")
        assert matches == []

    def test_multiple_pii_types(self):
        text = "Email user@test.com, SSN 123-45-6789"
        matches = detect_pii(text)
        types = {m.pii_type for m in matches}
        assert "email" in types
        assert "ssn" in types

    def test_match_has_correct_span(self):
        text = "Email: user@test.com today"
        matches = detect_pii(text)
        email_match = next(m for m in matches if m.pii_type == "email")
        assert text[email_match.start : email_match.end] == "user@test.com"

    def test_results_sorted_by_position(self):
        text = "SSN 123-45-6789 and email user@test.com"
        matches = detect_pii(text)
        positions = [m.start for m in matches]
        assert positions == sorted(positions)

    def test_empty_string_returns_empty(self):
        assert detect_pii("") == []


class TestHasPii:
    def test_returns_true_for_email(self):
        assert has_pii("Send to user@example.com") is True

    def test_returns_true_for_ssn(self):
        assert has_pii("SSN: 123-45-6789") is True

    def test_returns_false_for_clean_text(self):
        assert has_pii("I am a software engineer with 5 years experience") is False

    def test_returns_false_for_empty_string(self):
        assert has_pii("") is False


class TestRedactPii:
    def test_redacts_email(self):
        result = redact_pii("Contact user@example.com")
        assert "user@example.com" not in result
        assert "[REDACTED]" in result

    def test_redacts_ssn(self):
        result = redact_pii("SSN: 123-45-6789")
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_redacts_multiple_occurrences(self):
        result = redact_pii("a@b.com and c@d.com")
        assert "a@b.com" not in result
        assert "c@d.com" not in result
        assert result.count("[REDACTED]") == 2

    def test_clean_text_unchanged(self):
        text = "I am a Python developer"
        assert redact_pii(text) == text

    def test_custom_replacement(self):
        result = redact_pii("Email: a@b.com", replacement="***")
        assert "a@b.com" not in result
        assert "***" in result

    def test_preserves_surrounding_text(self):
        result = redact_pii("Hello user@test.com goodbye")
        assert result.startswith("Hello ")
        assert result.endswith(" goodbye")
