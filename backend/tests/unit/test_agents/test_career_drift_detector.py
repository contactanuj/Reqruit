"""Tests for CareerDriftDetectorAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.career_drift_detector import (
    CareerDriftDetectorAgent,
    career_drift_detector_agent,
)
from src.llm.models import TaskType


class TestCareerDriftDetectorInstantiation:
    def test_singleton_exists(self):
        assert career_drift_detector_agent is not None
        assert isinstance(career_drift_detector_agent, CareerDriftDetectorAgent)

    def test_task_type(self):
        agent = CareerDriftDetectorAgent()
        assert agent.task_type == TaskType.CAREER_ANALYSIS

    def test_name(self):
        agent = CareerDriftDetectorAgent()
        assert agent.name == "career_drift_detector"


class TestBuildMessages:
    def test_includes_role(self):
        agent = CareerDriftDetectorAgent()
        state = {"role_title": "Senior Backend Engineer"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Senior Backend Engineer" in messages[0].content

    def test_includes_industry(self):
        agent = CareerDriftDetectorAgent()
        state = {"role_title": "Engineer", "industry": "FinTech"}
        messages = agent.build_messages(state)
        assert "FinTech" in messages[0].content

    def test_includes_skills(self):
        agent = CareerDriftDetectorAgent()
        state = {"skills": ["Python", "AWS", "Kubernetes"]}
        messages = agent.build_messages(state)
        assert "Python" in messages[0].content
        assert "AWS" in messages[0].content

    def test_includes_goals(self):
        agent = CareerDriftDetectorAgent()
        state = {"career_goals": "Become a Staff Engineer"}
        messages = agent.build_messages(state)
        assert "Staff Engineer" in messages[0].content

    def test_includes_locale(self):
        agent = CareerDriftDetectorAgent()
        state = {"role_title": "Engineer", "locale": "India - Bangalore"}
        messages = agent.build_messages(state)
        assert "India - Bangalore" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = CareerDriftDetectorAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "general" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = CareerDriftDetectorAgent()
        response_data = {
            "overall_score": 72.5,
            "career_stage": "mid",
            "metrics": [
                {"name": "skill_relevance", "score": 80, "trend": "stable", "explanation": "Skills are current"},
            ],
            "drift_indicators": [
                {"category": "skill_gap", "severity": "medium", "description": "Missing cloud skills", "recommended_action": "Get AWS cert"},
            ],
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert result["overall_score"] == 72.5
        assert result["career_stage"] == "mid"
        assert len(result["metrics"]) == 1
        assert result["metrics"][0]["name"] == "skill_relevance"
        assert len(result["drift_indicators"]) == 1
        assert result["drift_indicators"][0]["category"] == "skill_gap"

    def test_parses_json_in_markdown_fences(self):
        agent = CareerDriftDetectorAgent()
        data = {
            "overall_score": 65.0,
            "career_stage": "early",
            "metrics": [{"name": "market_demand", "score": 70, "trend": "improving", "explanation": "Hot market"}],
            "drift_indicators": [],
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert result["overall_score"] == 65.0
        assert result["career_stage"] == "early"

    def test_fallback_on_invalid_json(self):
        agent = CareerDriftDetectorAgent()
        response = AIMessage(content="Your career looks healthy overall.")
        result = agent.process_response(response, {})

        assert result["overall_score"] == 50.0
        assert result["career_stage"] == "unknown"
        assert result["metrics"] == []
        assert result["drift_indicators"] == []
