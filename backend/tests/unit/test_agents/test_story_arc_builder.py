"""Tests for StoryArcBuilderAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.story_arc_builder import (
    StoryArcBuilderAgent,
    story_arc_builder_agent,
)
from src.llm.models import TaskType


class TestStoryArcBuilderInstantiation:
    def test_singleton_exists(self):
        assert story_arc_builder_agent is not None
        assert isinstance(story_arc_builder_agent, StoryArcBuilderAgent)

    def test_task_type(self):
        agent = StoryArcBuilderAgent()
        assert agent.task_type == TaskType.NARRATIVE_SYNTHESIS

    def test_name(self):
        agent = StoryArcBuilderAgent()
        assert agent.name == "story_arc_builder"


class TestBuildMessages:
    def test_includes_experiences(self):
        agent = StoryArcBuilderAgent()
        state = {"experiences": [{"company": "Acme", "role": "Engineer", "years": 3}]}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Acme" in messages[0].content

    def test_includes_achievements(self):
        agent = StoryArcBuilderAgent()
        state = {"achievements": ["Led migration to microservices", "Reduced latency by 40%"]}
        messages = agent.build_messages(state)
        assert "migration" in messages[0].content
        assert "latency" in messages[0].content

    def test_includes_feedback(self):
        agent = StoryArcBuilderAgent()
        state = {"feedback": "Make the narrative more leadership-focused"}
        messages = agent.build_messages(state)
        assert "leadership-focused" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = StoryArcBuilderAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "general" in messages[0].content.lower() or "narrative" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = StoryArcBuilderAgent()
        response_data = {
            "career_arc": {
                "theme": "From individual contributor to systems thinker",
                "summary": "A journey through scaling challenges",
                "key_transitions": ["IC to Tech Lead"],
            },
            "stories": [
                {
                    "title": "The Migration Story",
                    "strength_demonstrated": "Technical leadership",
                    "situation": "Legacy monolith slowing releases",
                    "task": "Lead microservices migration",
                    "action": "Designed service boundaries and led team of 5",
                    "result": "Deploy frequency increased 4x",
                    "best_used_for": "interviews about leadership",
                },
            ],
            "positioning_statement": "A backend engineer who turns complexity into clarity",
            "elevator_pitch": "I specialize in making systems scale gracefully.",
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert result["career_arc"]["theme"] == "From individual contributor to systems thinker"
        assert len(result["stories"]) == 1
        assert result["stories"][0]["title"] == "The Migration Story"
        assert "complexity" in result["positioning_statement"]
        assert "elevator_pitch" in result

    def test_parses_json_in_markdown_fences(self):
        agent = StoryArcBuilderAgent()
        data = {
            "career_arc": {"theme": "Builder to leader", "summary": "Growth story", "key_transitions": []},
            "stories": [{"title": "First PR", "strength_demonstrated": "Initiative"}],
            "positioning_statement": "Driven engineer",
            "elevator_pitch": "I build things.",
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert result["career_arc"]["theme"] == "Builder to leader"
        assert len(result["stories"]) == 1

    def test_fallback_on_invalid_json(self):
        agent = StoryArcBuilderAgent()
        response = AIMessage(content="Your career story is compelling and shows growth.")
        result = agent.process_response(response, {})

        assert result["career_arc"] == {}
        assert result["stories"] == []
        assert result["positioning_statement"] == ""
        assert result["elevator_pitch"] == ""
