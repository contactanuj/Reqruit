"""Tests for ScamDetectorAgent — Phase 4 trust verification."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.scam_detector import ScamDetectorAgent
from src.llm.models import TaskType


class TestScamDetectorConfig:
    def test_name(self) -> None:
        agent = ScamDetectorAgent()
        assert agent.name == "scam_detector"

    def test_task_type(self) -> None:
        agent = ScamDetectorAgent()
        assert agent.task_type == TaskType.SCAM_DETECTION

    def test_system_prompt_contains_verification_signals(self) -> None:
        agent = ScamDetectorAgent()
        assert "trust" in agent.system_prompt.lower() or "verification" in agent.system_prompt.lower()
        assert "MCA CIN" in agent.system_prompt
        assert "email" in agent.system_prompt.lower()


class TestBuildMessages:
    def test_includes_company_name(self) -> None:
        agent = ScamDetectorAgent()
        state = {"company_name": "Acme Corp"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Acme Corp" in messages[0].content

    def test_includes_registration_number(self) -> None:
        agent = ScamDetectorAgent()
        state = {"company_name": "Acme", "company_registration_number": "U12345MH2020PTC123456"}
        messages = agent.build_messages(state)
        assert "U12345MH2020PTC123456" in messages[0].content

    def test_includes_recruiter_email(self) -> None:
        agent = ScamDetectorAgent()
        state = {"company_name": "Acme", "recruiter_email": "hr@acme.com"}
        messages = agent.build_messages(state)
        assert "hr@acme.com" in messages[0].content

    def test_includes_linkedin_url(self) -> None:
        agent = ScamDetectorAgent()
        state = {"company_name": "Acme", "recruiter_linkedin_url": "https://linkedin.com/in/jdoe"}
        messages = agent.build_messages(state)
        assert "linkedin.com/in/jdoe" in messages[0].content

    def test_includes_job_url(self) -> None:
        agent = ScamDetectorAgent()
        state = {"company_name": "Acme", "job_url": "https://acme.com/jobs/123"}
        messages = agent.build_messages(state)
        assert "acme.com/jobs/123" in messages[0].content

    def test_missing_company_name_shows_not_provided(self) -> None:
        agent = ScamDetectorAgent()
        messages = agent.build_messages({})
        assert "Not provided" in messages[0].content


class TestProcessResponse:
    def test_valid_json_parsed(self) -> None:
        agent = ScamDetectorAgent()
        data = {
            "company_verification_score": 85.0,
            "recruiter_verification_score": 70.0,
            "posting_freshness_score": 90.0,
            "red_flag_count": 1,
            "overall_trust_score": 78.0,
            "risk_category": "LIKELY_SAFE",
            "risk_signals": [
                {"signal_type": "DOMAIN_NEW", "description": "Domain less than 1 year old", "severity": "medium"}
            ],
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})

        assert result["company_verification_score"] == 85.0
        assert result["recruiter_verification_score"] == 70.0
        assert result["overall_trust_score"] == 78.0
        assert result["risk_category"] == "LIKELY_SAFE"
        assert len(result["risk_signals"]) == 1

    def test_json_with_markdown_fences(self) -> None:
        agent = ScamDetectorAgent()
        data = {
            "company_verification_score": 60.0,
            "recruiter_verification_score": 40.0,
            "posting_freshness_score": 50.0,
            "red_flag_count": 2,
            "overall_trust_score": 45.0,
            "risk_category": "SUSPICIOUS",
            "risk_signals": [],
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        response = AIMessage(content=raw)
        result = agent.process_response(response, {})

        assert result["overall_trust_score"] == 45.0
        assert result["risk_category"] == "SUSPICIOUS"

    def test_malformed_json_returns_uncertain(self) -> None:
        agent = ScamDetectorAgent()
        response = AIMessage(content="This company looks suspicious but I can't parse...")
        result = agent.process_response(response, {})

        assert result["overall_trust_score"] == 50.0
        assert result["risk_category"] == "UNCERTAIN"
        assert len(result["risk_signals"]) == 1
        assert result["risk_signals"][0]["signal_type"] == "PARSE_FAILURE"

    def test_overall_trust_score_between_0_and_100(self) -> None:
        agent = ScamDetectorAgent()
        data = {
            "company_verification_score": 95.0,
            "recruiter_verification_score": 90.0,
            "posting_freshness_score": 100.0,
            "red_flag_count": 0,
            "overall_trust_score": 95.0,
            "risk_category": "VERIFIED",
            "risk_signals": [],
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})
        assert 0 <= result["overall_trust_score"] <= 100


class TestFullCall:
    async def test_agent_call_returns_trust_fields(self) -> None:
        from src.llm.models import ModelConfig, ProviderName

        agent = ScamDetectorAgent()
        manager = MagicMock()
        model = AsyncMock()
        config = ModelConfig(
            provider=ProviderName.OPENAI,
            model_name="gpt-4o-mini",
            max_tokens=2048,
            temperature=0.0,
        )
        manager.get_model_with_config.return_value = (model, config)
        manager.create_cost_callback.return_value = MagicMock()

        data = {
            "company_verification_score": 80.0,
            "recruiter_verification_score": 75.0,
            "posting_freshness_score": 85.0,
            "red_flag_count": 0,
            "overall_trust_score": 80.0,
            "risk_category": "LIKELY_SAFE",
            "risk_signals": [],
        }
        model.ainvoke.return_value = AIMessage(content=json.dumps(data))

        state = {"company_name": "Google", "recruiter_email": "hr@google.com"}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, {"configurable": {"user_id": "u1"}})

        assert result["overall_trust_score"] == 80.0
        assert result["risk_category"] == "LIKELY_SAFE"
