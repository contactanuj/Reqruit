"""Tests for OnboardingPlanAgent."""

import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from src.agents.onboarding_plan import (
    OnboardingPlanAgent,
    _parse_relationship_targets,
    onboarding_plan_agent,
)
from src.llm.models import TaskType


class TestOnboardingPlanAgentInstantiation:
    def test_singleton_exists(self):
        assert onboarding_plan_agent is not None
        assert isinstance(onboarding_plan_agent, OnboardingPlanAgent)

    def test_task_type(self):
        agent = OnboardingPlanAgent()
        assert agent.task_type == TaskType.ONBOARDING_PLANNING

    def test_name(self):
        agent = OnboardingPlanAgent()
        assert agent.name == "onboarding_plan"


class TestBuildMessages:
    def test_includes_company_and_role(self):
        agent = OnboardingPlanAgent()
        state = {"company_name": "Acme Corp", "role_title": "Senior Engineer"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        content = messages[0].content
        assert "Acme Corp" in content
        assert "Senior Engineer" in content

    def test_includes_skill_gaps(self):
        agent = OnboardingPlanAgent()
        state = {
            "company_name": "Test Co",
            "skill_gaps": [{"skill": "Kubernetes", "level": "beginner"}],
        }
        messages = agent.build_messages(state)
        assert "Kubernetes" in messages[0].content

    def test_includes_jd_text(self):
        agent = OnboardingPlanAgent()
        state = {"company_name": "Test Co", "jd_text": "We need a Python expert"}
        messages = agent.build_messages(state)
        assert "Python expert" in messages[0].content

    def test_includes_feedback(self):
        agent = OnboardingPlanAgent()
        state = {"company_name": "Test Co", "feedback": "Add more networking milestones"}
        messages = agent.build_messages(state)
        assert "networking milestones" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = OnboardingPlanAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "general" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = OnboardingPlanAgent()
        response_data = {
            "milestones": [
                {"title": "Meet team", "target_day": 1, "description": "Intro"},
                {"title": "Ship code", "target_day": 7, "description": "First PR"},
                {"title": "Own project", "target_day": 45, "description": "Feature"},
            ],
            "quick_wins": [
                {"title": "Fix a bug", "target_day": 3, "description": "Easy win"},
            ],
            "skill_gap_actions": [],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert "milestones" in result
        assert len(result["milestones"]) == 4  # 3 + 1 quick win

    def test_parses_json_in_markdown_fences(self):
        agent = OnboardingPlanAgent()
        json_str = json.dumps({
            "milestones": [{"title": "Test", "target_day": 1, "description": ""}],
            "quick_wins": [],
            "skill_gap_actions": [],
        })
        response = AIMessage(content=f"```json\n{json_str}\n```")
        result = agent.process_response(response, {})
        assert len(result["milestones"]) == 1

    def test_clamps_target_day(self):
        agent = OnboardingPlanAgent()
        response_data = {
            "milestones": [{"title": "Too late", "target_day": 120, "description": ""}],
            "quick_wins": [],
            "skill_gap_actions": [],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})
        assert result["milestones"][0]["target_day"] == 90

    def test_fallback_on_invalid_json(self):
        agent = OnboardingPlanAgent()
        response = AIMessage(content="This is not JSON")
        result = agent.process_response(response, {})
        assert "milestones" in result
        assert len(result["milestones"]) >= 3

    def test_creates_3_phases(self):
        agent = OnboardingPlanAgent()
        response_data = {
            "milestones": [
                {"title": "Learn", "target_day": 10, "description": "Phase 1"},
                {"title": "Contribute", "target_day": 45, "description": "Phase 2"},
                {"title": "Lead", "target_day": 75, "description": "Phase 3"},
            ],
            "quick_wins": [],
            "skill_gap_actions": [],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        days = [m["target_day"] for m in result["milestones"]]
        # Should have milestones across all 3 phases
        has_phase1 = any(d <= 30 for d in days)
        has_phase2 = any(31 <= d <= 60 for d in days)
        has_phase3 = any(61 <= d <= 90 for d in days)
        assert has_phase1
        assert has_phase2
        assert has_phase3

    def test_parses_relationship_targets(self):
        agent = OnboardingPlanAgent()
        response_data = {
            "milestones": [{"title": "Test", "target_day": 1, "description": ""}],
            "quick_wins": [],
            "skill_gap_actions": [],
            "relationship_targets": [
                {
                    "role": "Direct Manager",
                    "description": "Your primary reporting relationship",
                    "conversation_starters": ["What are team priorities?", "How is success measured?"],
                    "optimal_timing": "Week 1",
                },
                {
                    "role": "Skip-Level Manager",
                    "description": "Visibility into org direction",
                    "conversation_starters": ["What's the team vision?"],
                    "optimal_timing": "Week 2-3",
                },
            ],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})
        assert "relationship_targets" in result
        assert len(result["relationship_targets"]) == 2
        assert result["relationship_targets"][0]["role"] == "Direct Manager"
        assert len(result["relationship_targets"][0]["conversation_starters"]) == 2

    def test_relationship_targets_empty_on_fallback(self):
        agent = OnboardingPlanAgent()
        response = AIMessage(content="This is not JSON")
        result = agent.process_response(response, {})
        assert result["relationship_targets"] == []

    def test_relationship_targets_empty_when_missing(self):
        agent = OnboardingPlanAgent()
        response_data = {
            "milestones": [{"title": "Test", "target_day": 1, "description": ""}],
            "quick_wins": [],
            "skill_gap_actions": [],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})
        assert result["relationship_targets"] == []


class TestParseRelationshipTargets:
    def test_parses_valid_targets(self):
        parsed = {
            "relationship_targets": [
                {"role": "Manager", "description": "Boss", "conversation_starters": ["Hi"], "optimal_timing": "Week 1"},
                {"role": "Peer", "description": "Teammate"},
            ]
        }
        targets = _parse_relationship_targets(parsed)
        assert len(targets) == 2
        assert targets[0]["role"] == "Manager"
        assert targets[1]["conversation_starters"] == []
        assert targets[1]["optimal_timing"] == ""

    def test_skips_invalid_entries(self):
        parsed = {
            "relationship_targets": [
                {"role": "Manager"},
                "not a dict",
                {"no_role_key": True},
            ]
        }
        targets = _parse_relationship_targets(parsed)
        assert len(targets) == 1

    def test_returns_empty_when_key_missing(self):
        targets = _parse_relationship_targets({})
        assert targets == []
