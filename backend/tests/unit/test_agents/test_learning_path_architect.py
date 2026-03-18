"""Tests for LearningPathArchitectAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.learning_path_architect import (
    LearningPathArchitectAgent,
    learning_path_architect_agent,
)
from src.llm.models import TaskType


class TestLearningPathArchitectInstantiation:
    def test_singleton_exists(self):
        assert learning_path_architect_agent is not None
        assert isinstance(learning_path_architect_agent, LearningPathArchitectAgent)

    def test_task_type(self):
        agent = LearningPathArchitectAgent()
        assert agent.task_type == TaskType.LEARNING_PATH

    def test_name(self):
        agent = LearningPathArchitectAgent()
        assert agent.name == "learning_path_architect"


class TestBuildMessages:
    def test_includes_skills(self):
        agent = LearningPathArchitectAgent()
        state = {"current_skills": ["Python", "Django"], "target_skills": ["Kubernetes", "AWS"]}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Python" in messages[0].content
        assert "Kubernetes" in messages[0].content

    def test_includes_role(self):
        agent = LearningPathArchitectAgent()
        state = {"role_title": "Platform Engineer"}
        messages = agent.build_messages(state)
        assert "Platform Engineer" in messages[0].content

    def test_includes_budget(self):
        agent = LearningPathArchitectAgent()
        state = {"budget": "$500", "current_skills": ["Java"]}
        messages = agent.build_messages(state)
        assert "$500" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = LearningPathArchitectAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        # Empty state still gets hours_per_week default and the fallback check won't trigger,
        # but the message should contain learning-related content
        assert "10 hours/week" in messages[0].content


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = LearningPathArchitectAgent()
        response_data = {
            "learning_paths": [
                {
                    "skill": "System Design",
                    "current_level": "beginner",
                    "target_level": "advanced",
                    "estimated_hours": 120,
                    "priority": "high",
                    "resources": [
                        {"title": "Grokking System Design", "type": "course", "url": "https://example.com", "estimated_hours": 40, "cost": "$79"},
                    ],
                    "milestones": [
                        {"title": "Complete basics", "target_week": 4, "criteria": "Design a URL shortener"},
                    ],
                },
            ],
            "total_estimated_hours": 120,
            "recommended_schedule": "10 hours/week for 12 weeks",
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert len(result["learning_paths"]) == 1
        assert result["learning_paths"][0]["skill"] == "System Design"
        assert result["total_estimated_hours"] == 120
        assert "12 weeks" in result["recommended_schedule"]

    def test_parses_json_in_markdown_fences(self):
        agent = LearningPathArchitectAgent()
        data = {
            "learning_paths": [{"skill": "Docker", "priority": "medium"}],
            "total_estimated_hours": 40,
            "recommended_schedule": "5 hours/week",
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert result["learning_paths"][0]["skill"] == "Docker"
        assert result["total_estimated_hours"] == 40

    def test_fallback_on_invalid_json(self):
        agent = LearningPathArchitectAgent()
        response = AIMessage(content="I recommend starting with online courses.")
        result = agent.process_response(response, {})

        assert result["learning_paths"] == []
        assert result["total_estimated_hours"] == 0
        assert result["recommended_schedule"] == ""
