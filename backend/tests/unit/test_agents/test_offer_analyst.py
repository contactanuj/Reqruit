"""
Tests for OfferAnalystAgent.

Verifies agent configuration (task type, name), message construction
(build_messages), and response extraction (process_response). LLM calls
are not made — these tests focus on agent-specific logic.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.agents.offer_analyst import OfferAnalystAgent
from src.llm.models import ModelConfig, ProviderName, TaskType


class TestOfferAnalystAgentConfig:

    def test_task_type(self):
        agent = OfferAnalystAgent()
        assert agent.task_type == TaskType.OFFER_ANALYSIS

    def test_name(self):
        agent = OfferAnalystAgent()
        assert agent.name == "offer_analyst"

    def test_system_prompt_mentions_compensation(self):
        agent = OfferAnalystAgent()
        assert "compensation" in agent.system_prompt.lower()


class TestBuildMessages:

    def test_includes_offer_text(self):
        agent = OfferAnalystAgent()
        state = {
            "offer_text": "Your CTC is 25 LPA",
            "company_name": "Acme",
            "role_title": "SDE-2",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "25 LPA" in messages[0].content

    def test_includes_locale_context(self):
        agent = OfferAnalystAgent()
        state = {
            "offer_text": "Salary: $150,000",
            "company_name": "BigCo",
            "role_title": "Engineer",
            "locale_market": "US",
        }
        messages = agent.build_messages(state)
        assert "US" in messages[0].content

    def test_handles_empty_state(self):
        agent = OfferAnalystAgent()
        state = {}
        messages = agent.build_messages(state)
        assert len(messages) == 1


class TestProcessResponse:

    def test_extracts_components_from_json(self):
        agent = OfferAnalystAgent()
        llm_output = json.dumps({
            "components": [
                {"name": "Base Salary", "value": 1500000, "frequency": "annual", "is_guaranteed": True, "confidence": "high"},
                {"name": "Bonus", "value": 300000, "frequency": "annual", "is_guaranteed": False, "confidence": "medium"},
            ],
            "total_comp_annual": 1800000,
            "missing_fields": ["insurance_value"],
            "suggestions": ["Ask about health insurance coverage"],
        })
        response = AIMessage(content=llm_output)
        result = agent.process_response(response, {})

        assert len(result["components"]) == 2
        assert result["components"][0]["name"] == "Base Salary"
        assert result["total_comp_annual"] == 1800000
        assert result["missing_fields"] == ["insurance_value"]
        assert len(result["suggestions"]) == 1

    def test_handles_malformed_json(self):
        agent = OfferAnalystAgent()
        response = AIMessage(content="This is not JSON")
        result = agent.process_response(response, {})

        # Should return empty/default structure, not crash
        assert result["components"] == []
        assert result["total_comp_annual"] == 0.0

    def test_handles_json_with_markdown_fences(self):
        agent = OfferAnalystAgent()
        llm_output = '```json\n' + json.dumps({
            "components": [{"name": "Base", "value": 100000}],
            "total_comp_annual": 100000,
            "missing_fields": [],
            "suggestions": [],
        }) + '\n```'
        response = AIMessage(content=llm_output)
        result = agent.process_response(response, {})

        assert len(result["components"]) == 1
        assert result["total_comp_annual"] == 100000


class TestFullCall:

    async def test_call_returns_parsed_result(self):
        agent = OfferAnalystAgent()
        manager = MagicMock()
        model = AsyncMock()
        config = ModelConfig(
            provider=ProviderName.OPENAI,
            model_name="gpt-4o-mini",
            max_tokens=4096,
            temperature=0.0,
        )
        manager.get_model_with_config.return_value = (model, config)
        manager.create_cost_callback.return_value = MagicMock()

        llm_output = json.dumps({
            "components": [{"name": "Base", "value": 2000000}],
            "total_comp_annual": 2000000,
            "missing_fields": [],
            "suggestions": [],
        })
        model.ainvoke.return_value = AIMessage(content=llm_output)

        state = {
            "offer_text": "CTC 20 LPA",
            "company_name": "TestCo",
            "role_title": "SDE-1",
        }
        config_dict = {"configurable": {"user_id": "u1"}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, config_dict)

        assert result["total_comp_annual"] == 2000000
        assert len(result["components"]) == 1
