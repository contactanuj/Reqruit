"""Tests for CareerPathSimulatorAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.career_path_simulator import (
    CareerPathSimulatorAgent,
    career_path_simulator_agent,
)
from src.llm.models import TaskType


class TestCareerPathSimulatorInstantiation:
    def test_singleton_exists(self):
        assert career_path_simulator_agent is not None
        assert isinstance(career_path_simulator_agent, CareerPathSimulatorAgent)

    def test_task_type(self):
        agent = CareerPathSimulatorAgent()
        assert agent.task_type == TaskType.CAREER_ANALYSIS

    def test_name(self):
        agent = CareerPathSimulatorAgent()
        assert agent.name == "career_path_simulator"


class TestBuildMessages:
    def test_includes_role(self):
        agent = CareerPathSimulatorAgent()
        state = {"role_title": "Software Engineer"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Software Engineer" in messages[0].content

    def test_includes_skills(self):
        agent = CareerPathSimulatorAgent()
        state = {"skills": ["Python", "React", "PostgreSQL"]}
        messages = agent.build_messages(state)
        assert "Python" in messages[0].content
        assert "React" in messages[0].content

    def test_includes_locale(self):
        agent = CareerPathSimulatorAgent()
        state = {"role_title": "Engineer", "locale": "India - Hyderabad"}
        messages = agent.build_messages(state)
        assert "India - Hyderabad" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = CareerPathSimulatorAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "simulate" in messages[0].content.lower() or "software" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = CareerPathSimulatorAgent()
        response_data = {
            "scenarios": [
                {
                    "name": "best_case",
                    "probability": 0.2,
                    "timeline_years": 3,
                    "title_progression": ["Engineer -> Senior -> Lead"],
                    "milestones": ["Promotion to Senior"],
                    "salary_trajectory": {"year_1": "15L", "year_3": "30L"},
                    "risks": ["Market downturn"],
                    "actions_required": ["Upskill in system design"],
                },
            ],
            "india_insights": {
                "service_to_product_viability": "High",
                "gcc_opportunities": "Growing rapidly in Hyderabad",
                "key_considerations": ["Notice period negotiation"],
            },
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert len(result["scenarios"]) == 1
        assert result["scenarios"][0]["name"] == "best_case"
        assert result["india_insights"]["service_to_product_viability"] == "High"

    def test_parses_json_in_markdown_fences(self):
        agent = CareerPathSimulatorAgent()
        data = {
            "scenarios": [{"name": "most_likely", "probability": 0.6}],
            "india_insights": {"gcc_opportunities": "Strong"},
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert len(result["scenarios"]) == 1
        assert result["scenarios"][0]["name"] == "most_likely"

    def test_fallback_on_invalid_json(self):
        agent = CareerPathSimulatorAgent()
        response = AIMessage(content="Your career has many possible paths ahead.")
        result = agent.process_response(response, {})

        assert result["scenarios"] == []
        assert result["india_insights"] == {}
