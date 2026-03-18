"""Tests for QuestionPredictorAgent."""

from langchain_core.messages import HumanMessage

from src.agents.question_predictor import QuestionPredictorAgent
from src.llm.models import TaskType


class TestQuestionPredictorAgent:
    def test_name(self) -> None:
        agent = QuestionPredictorAgent()
        assert agent.name == "question_predictor"

    def test_task_type(self) -> None:
        agent = QuestionPredictorAgent()
        assert agent.task_type == TaskType.QUESTION_PREDICTION

    def test_has_system_prompt(self) -> None:
        agent = QuestionPredictorAgent()
        assert "predict" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = QuestionPredictorAgent()
        state = {
            "company_name": "Google",
            "role_title": "Senior SWE",
            "jd_analysis": "Requires distributed systems experience",
            "company_research": "Known for system design interviews",
            "locale_context": "US market",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Google" in messages[0].content
        assert "Senior SWE" in messages[0].content
        assert "distributed systems" in messages[0].content

    def test_build_messages_minimal(self) -> None:
        agent = QuestionPredictorAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1

    def test_build_messages_without_optional_fields(self) -> None:
        agent = QuestionPredictorAgent()
        state = {
            "company_name": "Acme",
            "role_title": "Engineer",
            "jd_analysis": "Python role",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Company Research" not in content
        assert "Locale Context" not in content

    def test_process_response(self) -> None:
        agent = QuestionPredictorAgent()

        class MockResponse:
            content = '[{"question_text": "Tell me about yourself", "question_type": "behavioral"}]'

        result = agent.process_response(MockResponse(), {})
        assert "predicted_questions" in result
        assert "Tell me about yourself" in result["predicted_questions"]
