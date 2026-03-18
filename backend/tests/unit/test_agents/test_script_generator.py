"""
Tests for ScriptGeneratorAgent — counter-offer scripts with decision trees.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.agents.script_generator import ScriptGeneratorAgent
from src.llm.models import TaskType


class TestScriptGeneratorConfig:

    def test_name(self):
        agent = ScriptGeneratorAgent()
        assert agent.name == "script_generator"

    def test_task_type(self):
        agent = ScriptGeneratorAgent()
        assert agent.task_type == TaskType.NEGOTIATION_COACHING

    def test_system_prompt_contains_branch_instructions(self):
        agent = ScriptGeneratorAgent()
        assert "acceptance" in agent.system_prompt.lower()
        assert "pushback" in agent.system_prompt.lower()
        assert "rejection" in agent.system_prompt.lower()

    def test_system_prompt_contains_risk_levels(self):
        agent = ScriptGeneratorAgent()
        assert "aggressive" in agent.system_prompt
        assert "moderate" in agent.system_prompt
        assert "safe" in agent.system_prompt


class TestBuildMessages:

    def test_includes_offer_context(self):
        agent = ScriptGeneratorAgent()
        state = {
            "offer_details": {
                "company_name": "Acme Corp",
                "role_title": "SDE-2",
                "total_comp_annual": 2500000,
                "locale_market": "IN",
            },
            "target_total_comp": 3000000,
            "user_priorities": ["salary", "remote_work"],
            "competing_offers": [],
            "market_data": {},
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Acme Corp" in messages[0].content
        assert "SDE-2" in messages[0].content
        assert "3000000" in messages[0].content

    def test_includes_non_salary_priorities(self):
        agent = ScriptGeneratorAgent()
        state = {
            "offer_details": {"company_name": "X"},
            "target_total_comp": 0,
            "user_priorities": ["remote_work", "equity_refresh", "title"],
            "competing_offers": [],
            "market_data": {},
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "remote_work" in content
        assert "equity_refresh" in content
        assert "title" in content

    def test_dict_priorities_handled(self):
        agent = ScriptGeneratorAgent()
        state = {
            "offer_details": {"company_name": "X"},
            "target_total_comp": 0,
            "user_priorities": {"remote_work": True, "signing_bonus": 50000},
            "competing_offers": [],
            "market_data": {},
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "remote_work" in content

    def test_competing_offers_mentioned(self):
        agent = ScriptGeneratorAgent()
        state = {
            "offer_details": {"company_name": "X"},
            "target_total_comp": 0,
            "user_priorities": [],
            "competing_offers": [{"company": "Y", "total": 3000000}],
            "market_data": {},
        }
        messages = agent.build_messages(state)
        assert "1 other offer" in messages[0].content


class TestProcessResponse:

    def test_valid_json_response(self):
        agent = ScriptGeneratorAgent()
        data = {
            "opening_statement": "I'd like to discuss the compensation.",
            "branches": [
                {
                    "scenario_name": "acceptance",
                    "recruiter_response": "We can do that.",
                    "recommended_user_response": "Great, let's formalize.",
                    "reasoning": "Lock in the win.",
                    "risk_assessment": "safe",
                },
                {
                    "scenario_name": "pushback",
                    "recruiter_response": "That's above our range.",
                    "recommended_user_response": "I understand, but market data shows...",
                    "reasoning": "Use data anchoring.",
                    "risk_assessment": "moderate",
                },
                {
                    "scenario_name": "rejection",
                    "recruiter_response": "We can't go higher.",
                    "recommended_user_response": "What about non-salary items?",
                    "reasoning": "Pivot to total package.",
                    "risk_assessment": "safe",
                },
            ],
            "non_salary_tactics": [
                {"priority": "remote_work", "script": "Could we discuss...", "fallback": "Hybrid?"}
            ],
            "general_tips": ["Stay calm", "Use silence"],
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})

        assert result["opening_statement"] == "I'd like to discuss the compensation."
        assert len(result["branches"]) == 3
        assert result["branches"][0]["scenario_name"] == "acceptance"
        assert result["branches"][1]["risk_assessment"] == "moderate"
        assert len(result["non_salary_tactics"]) == 1
        assert len(result["general_tips"]) == 2

    def test_json_with_markdown_fences(self):
        agent = ScriptGeneratorAgent()
        data = {
            "opening_statement": "Hello",
            "branches": [{"scenario_name": "test", "recruiter_response": "ok", "recommended_user_response": "thanks", "reasoning": "polite", "risk_assessment": "safe"}],
            "non_salary_tactics": [],
            "general_tips": [],
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        response = AIMessage(content=raw)
        result = agent.process_response(response, {})

        assert result["opening_statement"] == "Hello"
        assert len(result["branches"]) == 1

    def test_malformed_json_fallback(self):
        agent = ScriptGeneratorAgent()
        response = AIMessage(content="Not valid JSON at all")
        result = agent.process_response(response, {})

        assert result["opening_statement"] == "Not valid JSON at all"
        assert result["branches"] == []
        assert result["non_salary_tactics"] == []

    async def test_full_call_returns_structured_result(self):
        from src.llm.models import ModelConfig, ProviderName

        agent = ScriptGeneratorAgent()
        manager = MagicMock()
        model = AsyncMock()
        config = ModelConfig(
            provider=ProviderName.ANTHROPIC,
            model_name="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            temperature=0.7,
        )
        manager.get_model_with_config.return_value = (model, config)
        manager.create_cost_callback.return_value = MagicMock()

        data = {
            "opening_statement": "I appreciate the offer.",
            "branches": [
                {
                    "scenario_name": "acceptance",
                    "recruiter_response": "Done.",
                    "recommended_user_response": "Great.",
                    "reasoning": "Win.",
                    "risk_assessment": "safe",
                }
            ],
            "non_salary_tactics": [],
            "general_tips": ["Be confident"],
        }
        model.ainvoke.return_value = AIMessage(content=json.dumps(data))

        state = {
            "offer_details": {"company_name": "Test"},
            "target_total_comp": 3000000,
            "user_priorities": ["salary"],
            "competing_offers": [],
            "market_data": {},
        }

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, {"configurable": {"user_id": "u1"}})

        assert result["opening_statement"] == "I appreciate the offer."
        assert len(result["branches"]) == 1
