"""Tests for SkillsAnalyst agent."""

from langchain_core.messages import HumanMessage

from src.agents.skills_analyst import SkillsAnalyst
from src.llm.models import TaskType


class TestSkillsAnalyst:
    def test_name(self) -> None:
        agent = SkillsAnalyst()
        assert agent.name == "skills_analyst"

    def test_task_type(self) -> None:
        agent = SkillsAnalyst()
        assert agent.task_type == TaskType.SKILLS_ANALYSIS

    def test_has_system_prompt(self) -> None:
        agent = SkillsAnalyst()
        assert "skills" in agent.system_prompt.lower()

    def test_build_messages_with_data(self) -> None:
        agent = SkillsAnalyst()
        state = {
            "resume_text": "Python developer with 5 years experience",
            "mined_achievements": '[{"title": "Built API"}]',
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Python developer" in messages[0].content
        assert "Built API" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = SkillsAnalyst()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No data provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = SkillsAnalyst()

        class MockResponse:
            content = '{"skills": [], "summary": "Junior developer"}'

        result = agent.process_response(MockResponse(), {})
        assert result == {"skills_analysis": '{"skills": [], "summary": "Junior developer"}'}
