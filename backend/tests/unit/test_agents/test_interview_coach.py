"""Tests for InterviewCoachAgent."""

from langchain_core.messages import HumanMessage

from src.agents.interview_coach import InterviewCoachAgent
from src.llm.models import TaskType


class TestInterviewCoachAgent:
    def test_name(self) -> None:
        agent = InterviewCoachAgent()
        assert agent.name == "interview_coach"

    def test_task_type(self) -> None:
        agent = InterviewCoachAgent()
        assert agent.task_type == TaskType.INTERVIEW_COACHING

    def test_has_system_prompt(self) -> None:
        agent = InterviewCoachAgent()
        assert "interview coach" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = InterviewCoachAgent()
        state = {
            "current_question": "Tell me about a time you led a team.",
            "user_answer": "I led a team of 5 engineers to build a new API.",
            "star_stories": "Led API team: Situation...",
            "difficulty_level": "medium",
            "session_scores": [{"score_relevance": 4}],
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "led a team" in messages[0].content
        assert "5 engineers" in messages[0].content
        assert "STAR Stories" in messages[0].content

    def test_build_messages_minimal(self) -> None:
        agent = InterviewCoachAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1

    def test_build_messages_without_optional_fields(self) -> None:
        agent = InterviewCoachAgent()
        state = {
            "current_question": "Describe a challenge.",
            "user_answer": "I faced a tight deadline.",
            "difficulty_level": "easy",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "STAR Stories" not in content
        assert "Session Scores" not in content

    def test_process_response(self) -> None:
        agent = InterviewCoachAgent()

        class MockResponse:
            content = '{"score_relevance": 4, "score_structure": 3, "feedback": "Good structure"}'

        result = agent.process_response(MockResponse(), {})
        assert "evaluation" in result
        assert "score_relevance" in result["evaluation"]
