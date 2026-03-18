"""Tests for FitScorer agent."""

from langchain_core.messages import HumanMessage

from src.agents.fit_scorer import FitScorer
from src.llm.models import TaskType


class TestFitScorer:
    def test_name(self) -> None:
        agent = FitScorer()
        assert agent.name == "fit_scorer"

    def test_task_type(self) -> None:
        agent = FitScorer()
        assert agent.task_type == TaskType.DATA_EXTRACTION

    def test_has_system_prompt(self) -> None:
        agent = FitScorer()
        assert "fit" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = FitScorer()
        state = {
            "skills_profile": {"skills": [{"name": "Python"}]},
            "jd_analysis": {"required_skills": ["Python", "Go"]},
            "job_description": "Senior Backend Engineer",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Python" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = FitScorer()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No data provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = FitScorer()

        class MockResponse:
            content = '{"overall": 85.0, "matching_skills": ["Python"]}'

        result = agent.process_response(MockResponse(), {})
        assert result == {"fit_assessment": '{"overall": 85.0, "matching_skills": ["Python"]}'}
