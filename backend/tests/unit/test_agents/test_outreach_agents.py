"""
Unit tests for OutreachComposer agent.

Coverage:
- Agent configuration (name, task_type)
- build_messages includes all context fields
- process_response strips content cleanly
"""

from langchain_core.messages import AIMessage

from src.agents.outreach import OutreachComposer
from src.llm.models import TaskType


class TestOutreachComposerConfig:
    def test_name(self):
        agent = OutreachComposer()
        assert agent.name == "outreach_composer"

    def test_task_type(self):
        agent = OutreachComposer()
        assert agent.task_type == TaskType.OUTREACH_MESSAGE


class TestOutreachComposerBuildMessages:
    def test_includes_all_context(self):
        agent = OutreachComposer()
        state = {
            "role_title": "Software Engineer",
            "company_name": "Acme Corp",
            "contact_name": "Jane Smith",
            "contact_role": "Engineering Manager",
            "message_type": "manager",
            "job_description": "Build scalable systems...",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        content = messages[0].content
        assert "Software Engineer" in content
        assert "Acme Corp" in content
        assert "Jane Smith" in content
        assert "Engineering Manager" in content
        assert "manager" in content
        assert "Build scalable" in content

    def test_handles_empty_state(self):
        agent = OutreachComposer()
        messages = agent.build_messages({})
        assert len(messages) == 1


class TestOutreachComposerProcessResponse:
    def test_extracts_content(self):
        agent = OutreachComposer()
        response = AIMessage(content="Hi Jane, I noticed your team...")
        result = agent.process_response(response, {})
        assert result["content"] == "Hi Jane, I noticed your team..."

    def test_strips_wrapping_quotes(self):
        agent = OutreachComposer()
        response = AIMessage(content='"Hi Jane, I noticed your team..."')
        result = agent.process_response(response, {})
        assert result["content"] == "Hi Jane, I noticed your team..."

    def test_strips_whitespace(self):
        agent = OutreachComposer()
        response = AIMessage(content="  Hello there.  \n")
        result = agent.process_response(response, {})
        assert result["content"] == "Hello there."
