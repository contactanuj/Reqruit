"""
Tests for company-specific prompt injection in QuestionPredictorAgent (Story 9.5).
"""

from src.agents.company_patterns import get_company_pattern
from src.agents.question_predictor import QuestionPredictorAgent


def _base_state(**overrides):
    state = {
        "company_name": "TestCo",
        "role_title": "Engineer",
        "jd_analysis": "Python developer",
        "company_research": "",
        "locale_context": "",
        "company_pattern": "",
        "round_type": "",
    }
    state.update(overrides)
    return state


class TestCompanyPatternInjection:
    def test_includes_amazon_criteria(self) -> None:
        agent = QuestionPredictorAgent()
        pattern = get_company_pattern("Amazon")
        state = _base_state(
            company_name="Amazon",
            company_pattern=pattern.model_dump_json(),
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company Interview Pattern" in content
        assert "question_weights" in content.lower() or "behavioral" in content

    def test_includes_google_criteria(self) -> None:
        agent = QuestionPredictorAgent()
        pattern = get_company_pattern("Google")
        state = _base_state(
            company_name="Google",
            company_pattern=pattern.model_dump_json(),
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company Interview Pattern" in content

    def test_no_pattern_graceful(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(company_pattern="")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company Interview Pattern" not in content
        assert "Predict the 10 most likely" in content

    def test_invalid_json_pattern_graceful(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(company_pattern="not valid json")
        messages = agent.build_messages(state)
        # Should not crash, just skip pattern injection
        assert len(messages) == 1


class TestRoundTypeInjection:
    def test_aptitude_round(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(round_type="aptitude")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "aptitude" in content.lower()

    def test_gd_round(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(round_type="gd")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "gd" in content.lower()

    def test_behavioral_round_no_extra_injection(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(round_type="behavioral")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Round Type" not in content

    def test_empty_round_type_no_injection(self) -> None:
        agent = QuestionPredictorAgent()
        state = _base_state(round_type="")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Round Type" not in content
