"""Tests for ServiceCompanyExitPlannerAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.service_exit_planner import (
    ServiceCompanyExitPlannerAgent,
    service_exit_planner_agent,
)
from src.llm.models import TaskType


class TestServiceCompanyExitPlannerInstantiation:
    def test_singleton_exists(self):
        assert service_exit_planner_agent is not None
        assert isinstance(service_exit_planner_agent, ServiceCompanyExitPlannerAgent)

    def test_task_type(self):
        agent = ServiceCompanyExitPlannerAgent()
        assert agent.task_type == TaskType.SERVICE_EXIT_PLANNING

    def test_name(self):
        agent = ServiceCompanyExitPlannerAgent()
        assert agent.name == "service_exit_planner"


class TestBuildMessages:
    def test_includes_company(self):
        agent = ServiceCompanyExitPlannerAgent()
        state = {"current_company": "TCS"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "TCS" in messages[0].content

    def test_includes_role(self):
        agent = ServiceCompanyExitPlannerAgent()
        state = {"role_title": "Systems Engineer", "current_company": "Infosys"}
        messages = agent.build_messages(state)
        assert "Systems Engineer" in messages[0].content

    def test_includes_skills(self):
        agent = ServiceCompanyExitPlannerAgent()
        state = {"skills": ["Java", "Spring Boot", "SQL"]}
        messages = agent.build_messages(state)
        assert "Java" in messages[0].content
        assert "Spring Boot" in messages[0].content

    def test_includes_notice_period(self):
        agent = ServiceCompanyExitPlannerAgent()
        state = {"notice_period_days": 90, "current_company": "Wipro"}
        messages = agent.build_messages(state)
        assert "90" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = ServiceCompanyExitPlannerAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        # Empty state still gets company_type default
        assert "service" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = ServiceCompanyExitPlannerAgent()
        response_data = {
            "readiness_score": 55,
            "skill_gaps": [
                {"skill": "System Design", "current": "basic", "required": "advanced", "action": "Practice on mock interviews"},
            ],
            "resume_strategy": {
                "key_changes": ["Reframe project descriptions"],
                "project_reframing": ["Client project -> Product feature"],
            },
            "interview_prep": {
                "focus_areas": ["DSA", "System Design"],
                "estimated_prep_months": 4,
                "weekly_plan": "10 hours/week",
            },
            "target_companies": {
                "tier_1": ["Google", "Microsoft"],
                "tier_2": ["Flipkart", "Swiggy"],
                "tier_3": ["Well-funded startups"],
            },
            "timeline": [
                {"month": 1, "focus": "DSA fundamentals", "milestones": ["Complete 100 LC problems"]},
            ],
            "compensation_insights": {
                "current_range": "8-12 LPA",
                "expected_range": "18-30 LPA",
                "negotiation_tips": ["Leverage competing offers"],
            },
            "notice_period_strategy": "Start interviewing 3 months before planned exit",
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert result["readiness_score"] == 55
        assert len(result["skill_gaps"]) == 1
        assert result["skill_gaps"][0]["skill"] == "System Design"
        assert "Reframe" in result["resume_strategy"]["key_changes"][0]
        assert result["interview_prep"]["estimated_prep_months"] == 4
        assert "Google" in result["target_companies"]["tier_1"]
        assert len(result["timeline"]) == 1
        assert "18-30 LPA" in result["compensation_insights"]["expected_range"]
        assert "3 months" in result["notice_period_strategy"]

    def test_parses_json_in_markdown_fences(self):
        agent = ServiceCompanyExitPlannerAgent()
        data = {
            "readiness_score": 70,
            "skill_gaps": [{"skill": "DSA", "current": "intermediate", "required": "advanced", "action": "Practice"}],
            "resume_strategy": {},
            "interview_prep": {},
            "target_companies": {},
            "timeline": [],
            "compensation_insights": {},
            "notice_period_strategy": "Buy out notice period",
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert result["readiness_score"] == 70
        assert result["skill_gaps"][0]["skill"] == "DSA"

    def test_fallback_on_invalid_json(self):
        agent = ServiceCompanyExitPlannerAgent()
        response = AIMessage(content="You should focus on system design and DSA.")
        result = agent.process_response(response, {})

        assert result["readiness_score"] == 0
        assert result["skill_gaps"] == []
        assert result["resume_strategy"] == {}
        assert result["interview_prep"] == {}
        assert result["target_companies"] == {}
        assert result["timeline"] == []
        assert result["compensation_insights"] == {}
        assert result["notice_period_strategy"] == ""
