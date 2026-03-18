"""
Tests for company interview patterns (Story 9.5).
"""

from src.agents.company_patterns import (
    CAMPUS_PLACEMENT_ROUNDS,
    CompanyInterviewPattern,
    get_company_pattern,
    get_default_pattern,
)


class TestGetCompanyPattern:
    def test_amazon_pattern(self) -> None:
        pattern = get_company_pattern("Amazon")
        assert pattern is not None
        assert pattern.company_name == "Amazon"
        assert pattern.question_weights["behavioral"] > pattern.question_weights["technical"]
        assert any("Leadership Principles" in c for c in pattern.evaluation_criteria)

    def test_google_pattern(self) -> None:
        pattern = get_company_pattern("Google")
        assert pattern is not None
        assert pattern.company_name == "Google"
        assert pattern.question_weights["technical"] > pattern.question_weights["behavioral"]

    def test_microsoft_pattern(self) -> None:
        pattern = get_company_pattern("Microsoft")
        assert pattern is not None
        assert any("Growth Mindset" in c for c in pattern.evaluation_criteria)

    def test_tcs_campus_pattern(self) -> None:
        pattern = get_company_pattern("TCS")
        assert pattern is not None
        assert "aptitude" in pattern.interview_stages

    def test_infosys_pattern(self) -> None:
        pattern = get_company_pattern("Infosys")
        assert pattern is not None

    def test_case_insensitive_lookup(self) -> None:
        assert get_company_pattern("amazon") is not None
        assert get_company_pattern("AMAZON") is not None
        assert get_company_pattern("Amazon") is not None

    def test_unknown_company_returns_none(self) -> None:
        assert get_company_pattern("UnknownStartup123") is None

    def test_fuzzy_match_startswith(self) -> None:
        pattern = get_company_pattern("amaz")
        assert pattern is not None
        assert pattern.company_name == "Amazon"


class TestGetDefaultPattern:
    def test_returns_generic(self) -> None:
        pattern = get_default_pattern()
        assert pattern.company_name == "Generic"
        assert len(pattern.question_weights) > 0
        assert len(pattern.evaluation_criteria) > 0

    def test_balanced_weights(self) -> None:
        pattern = get_default_pattern()
        weights = list(pattern.question_weights.values())
        assert max(weights) - min(weights) <= 0.2


class TestCompanyInterviewPattern:
    def test_serialization_roundtrip(self) -> None:
        pattern = get_company_pattern("Amazon")
        serialized = pattern.model_dump_json()
        restored = CompanyInterviewPattern.model_validate_json(serialized)
        assert restored.company_name == "Amazon"
        assert restored.question_weights == pattern.question_weights

    def test_model_dump(self) -> None:
        pattern = get_default_pattern()
        data = pattern.model_dump()
        assert isinstance(data["question_weights"], dict)
        assert isinstance(data["evaluation_criteria"], list)


class TestCampusPlacementRounds:
    def test_round_order(self) -> None:
        assert CAMPUS_PLACEMENT_ROUNDS == ["aptitude", "gd", "technical", "hr"]

    def test_four_rounds(self) -> None:
        assert len(CAMPUS_PLACEMENT_ROUNDS) == 4
