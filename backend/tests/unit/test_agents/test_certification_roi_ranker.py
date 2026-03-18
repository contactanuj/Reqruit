"""Tests for CertificationROIRankerAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.certification_roi_ranker import (
    CertificationROIRankerAgent,
    certification_roi_ranker_agent,
)
from src.llm.models import TaskType


class TestCertificationROIRankerInstantiation:
    def test_singleton_exists(self):
        assert certification_roi_ranker_agent is not None
        assert isinstance(certification_roi_ranker_agent, CertificationROIRankerAgent)

    def test_task_type(self):
        agent = CertificationROIRankerAgent()
        assert agent.task_type == TaskType.CERTIFICATION_ROI

    def test_name(self):
        agent = CertificationROIRankerAgent()
        assert agent.name == "certification_roi_ranker"


class TestBuildMessages:
    def test_includes_role(self):
        agent = CertificationROIRankerAgent()
        state = {"role_title": "DevOps Engineer"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "DevOps Engineer" in messages[0].content

    def test_includes_skills(self):
        agent = CertificationROIRankerAgent()
        state = {"skills": ["Docker", "Terraform", "CI/CD"]}
        messages = agent.build_messages(state)
        assert "Docker" in messages[0].content
        assert "Terraform" in messages[0].content

    def test_includes_locale(self):
        agent = CertificationROIRankerAgent()
        state = {"role_title": "Engineer", "locale": "India - Pune"}
        messages = agent.build_messages(state)
        assert "India - Pune" in messages[0].content

    def test_includes_existing_certifications(self):
        agent = CertificationROIRankerAgent()
        state = {"existing_certifications": ["AWS Cloud Practitioner", "CKA"]}
        messages = agent.build_messages(state)
        assert "AWS Cloud Practitioner" in messages[0].content
        assert "CKA" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = CertificationROIRankerAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "certifications" in messages[0].content.lower() or "software" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = CertificationROIRankerAgent()
        response_data = {
            "certifications": [
                {
                    "name": "AWS Solutions Architect - Associate",
                    "provider": "Amazon Web Services",
                    "roi_score": 85,
                    "cost_usd": 300,
                    "study_hours": 120,
                    "salary_impact_pct": 15,
                    "market_demand": "high",
                    "relevance": "high",
                    "locale_bonus": "India GCC market values AWS heavily",
                    "recommendation": "Strongly recommended",
                    "prep_resources": ["A Cloud Guru"],
                },
            ],
            "top_recommendation": "Start with AWS Solutions Architect",
            "locale_insights": "AWS and Azure certs are most valued in India GCC market",
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert len(result["certifications"]) == 1
        assert result["certifications"][0]["roi_score"] == 85
        assert "AWS" in result["top_recommendation"]
        assert "GCC" in result["locale_insights"]

    def test_parses_json_in_markdown_fences(self):
        agent = CertificationROIRankerAgent()
        data = {
            "certifications": [{"name": "CKA", "roi_score": 78}],
            "top_recommendation": "Get CKA first",
            "locale_insights": "Kubernetes skills in high demand",
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        assert result["certifications"][0]["name"] == "CKA"
        assert result["top_recommendation"] == "Get CKA first"

    def test_fallback_on_invalid_json(self):
        agent = CertificationROIRankerAgent()
        response = AIMessage(content="I recommend getting AWS certified first.")
        result = agent.process_response(response, {})

        assert result["certifications"] == []
        assert result["top_recommendation"] == ""
        assert result["locale_insights"] == ""
