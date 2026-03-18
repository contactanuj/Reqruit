"""Tests for JDDecoder agent."""

from langchain_core.messages import HumanMessage

from src.agents.jd_decoder import JDDecoder
from src.llm.models import TaskType


class TestJDDecoder:
    def test_name(self) -> None:
        agent = JDDecoder()
        assert agent.name == "jd_decoder"

    def test_task_type(self) -> None:
        agent = JDDecoder()
        assert agent.task_type == TaskType.DATA_EXTRACTION

    def test_has_system_prompt(self) -> None:
        agent = JDDecoder()
        assert "job description" in agent.system_prompt.lower()

    def test_build_messages_with_jd(self) -> None:
        agent = JDDecoder()
        state = {
            "job_description": "We are looking for a Senior Python Engineer with 5+ years experience in FastAPI and PostgreSQL.",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Senior Python Engineer" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = JDDecoder()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No job description provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = JDDecoder()

        class MockResponse:
            content = '{"required_skills": ["Python", "FastAPI"]}'

        result = agent.process_response(MockResponse(), {})
        assert result == {"jd_analysis": '{"required_skills": ["Python", "FastAPI"]}'}
