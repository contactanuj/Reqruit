"""
Tests for company-specific and round-specific prompt injection in InterviewCoachAgent (Story 9.5).
"""

from src.agents.company_patterns import get_company_pattern
from src.agents.interview_coach import InterviewCoachAgent


def _base_state(**overrides):
    state = {
        "current_question": "Tell me about yourself",
        "user_answer": "I am a software engineer with 5 years experience.",
        "star_stories": "",
        "difficulty_level": "medium",
        "session_scores": [],
        "round_type": "",
        "company_pattern": "",
        "locale_context": "",
    }
    state.update(overrides)
    return state


class TestGDRoundPrompt:
    def test_includes_gd_coaching(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(
            round_type="gd",
            current_question="Discuss: Should AI replace teachers?",
            user_answer="I believe AI should augment, not replace...",
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "GD Coaching Mode" in content
        assert "opening" in content.lower() or "Opening" in content

    def test_gd_includes_data_points(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(round_type="gd")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "data points" in content.lower()

    def test_gd_includes_perspective_balance(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(round_type="gd")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "perspective" in content.lower()


class TestHRRoundPrompt:
    def test_includes_hr_coaching(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(
            round_type="hr",
            current_question="What are your salary expectations?",
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "HR Round Coaching" in content
        assert "CTC" in content

    def test_includes_notice_period(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(round_type="hr")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "notice period" in content.lower() or "Notice period" in content

    def test_includes_relocation(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(round_type="hr")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "relocation" in content.lower() or "Relocation" in content

    def test_injects_locale_context(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(
            round_type="hr",
            locale_context="India market: CTC includes base + HRA + special allowances",
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Locale Context" in content
        assert "HRA" in content

    def test_no_locale_context_still_works(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(round_type="hr", locale_context="")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "HR Round Coaching" in content
        assert "Locale Context" not in content


class TestCompanySpecificCriteria:
    def test_amazon_lp_criteria(self) -> None:
        agent = InterviewCoachAgent()
        pattern = get_company_pattern("Amazon")
        state = _base_state(company_pattern=pattern.model_dump_json())
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company-Specific Evaluation Criteria" in content
        assert "Leadership Principles" in content

    def test_google_criteria(self) -> None:
        agent = InterviewCoachAgent()
        pattern = get_company_pattern("Google")
        state = _base_state(company_pattern=pattern.model_dump_json())
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company-Specific Evaluation Criteria" in content
        assert "Googleyness" in content

    def test_no_pattern_uses_generic(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(company_pattern="")
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company-Specific Evaluation Criteria" not in content

    def test_gd_takes_precedence_over_company(self) -> None:
        """GD round prompt should appear instead of company criteria."""
        agent = InterviewCoachAgent()
        pattern = get_company_pattern("Amazon")
        state = _base_state(
            round_type="gd",
            company_pattern=pattern.model_dump_json(),
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "GD Coaching Mode" in content
        assert "Company-Specific Evaluation Criteria" not in content

    def test_hr_takes_precedence_over_company(self) -> None:
        """HR round prompt should appear instead of company criteria."""
        agent = InterviewCoachAgent()
        pattern = get_company_pattern("Amazon")
        state = _base_state(
            round_type="hr",
            company_pattern=pattern.model_dump_json(),
        )
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "HR Round Coaching" in content
        assert "Company-Specific Evaluation Criteria" not in content

    def test_invalid_json_pattern_graceful(self) -> None:
        agent = InterviewCoachAgent()
        state = _base_state(company_pattern="not valid json")
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Company-Specific Evaluation Criteria" not in messages[0].content
