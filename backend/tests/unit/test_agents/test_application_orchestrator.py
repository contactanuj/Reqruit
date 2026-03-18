"""Tests for ApplicationOrchestratorAgent."""

from langchain_core.messages import HumanMessage

from src.agents.application_orchestrator import ApplicationOrchestratorAgent
from src.llm.models import TaskType


class TestApplicationOrchestratorAgent:
    def test_name(self) -> None:
        agent = ApplicationOrchestratorAgent()
        assert agent.name == "application_orchestrator"

    def test_task_type(self) -> None:
        agent = ApplicationOrchestratorAgent()
        assert agent.task_type == TaskType.APPLICATION_ORCHESTRATION

    def test_has_system_prompt(self) -> None:
        agent = ApplicationOrchestratorAgent()
        assert "application strategist" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = ApplicationOrchestratorAgent()
        state = {
            "jd_analysis": "Requires Python, FastAPI, 5 years experience",
            "fit_analysis": "Strong match on Python, gap on K8s",
            "skills_summary": "Senior backend engineer",
            "locale_context": "India, Naukri platform",
            "relevant_resume_blocks": "Block 1: Python projects",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Python, FastAPI" in messages[0].content
        assert "Naukri" in messages[0].content
        assert "Block 1" in messages[0].content

    def test_build_messages_minimal(self) -> None:
        agent = ApplicationOrchestratorAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)

    def test_build_messages_without_optional_fields(self) -> None:
        agent = ApplicationOrchestratorAgent()
        state = {
            "jd_analysis": "Backend role",
            "fit_analysis": "Good fit",
            "skills_summary": "Python dev",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Locale Context" not in content
        assert "Available Resume Blocks" not in content

    def test_process_response(self) -> None:
        agent = ApplicationOrchestratorAgent()

        class MockResponse:
            content = '{"recommended_resume_blocks": ["Python"], "cover_letter_tone": "professional"}'

        result = agent.process_response(MockResponse(), {})
        assert "application_strategy" in result
        assert "recommended_resume_blocks" in result["application_strategy"]
