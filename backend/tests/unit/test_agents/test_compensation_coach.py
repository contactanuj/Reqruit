"""
Tests for CompensationCoachAgent — salary anchoring script generation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.agents.compensation_coach import CompensationCoachAgent
from src.llm.models import TaskType


class TestCompensationCoachConfig:

    def test_name(self):
        agent = CompensationCoachAgent()
        assert agent.name == "compensation_coach"

    def test_task_type(self):
        agent = CompensationCoachAgent()
        assert agent.task_type == TaskType.NEGOTIATION_COACHING

    def test_system_prompt_contains_locale_rules(self):
        agent = CompensationCoachAgent()
        assert "IN" in agent.system_prompt
        assert "US" in agent.system_prompt
        assert "CTC" in agent.system_prompt
        assert "market" in agent.system_prompt.lower()


class TestBuildMessages:

    def test_india_locale_uses_ctc(self):
        agent = CompensationCoachAgent()
        state = {
            "locale": "IN",
            "current_ctc": 1500000,
            "target_range_min": 2000000,
            "target_range_max": 2500000,
            "role_title": "SDE-2",
            "company_name": "Acme Corp",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        content = messages[0].content
        assert "Current CTC" in content
        assert "1500000" in content
        assert "SDE-2" in content
        assert "Acme Corp" in content

    def test_us_locale_uses_salary(self):
        agent = CompensationCoachAgent()
        state = {
            "locale": "US",
            "current_salary": 150000,
            "target_range_min": 180000,
            "target_range_max": 220000,
            "role_title": "Staff Engineer",
            "company_name": "BigTech Inc",
            "city": "San Francisco",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Current salary" in content
        assert "150000" in content
        assert "San Francisco" in content

    def test_company_context_included(self):
        agent = CompensationCoachAgent()
        state = {
            "locale": "IN",
            "current_ctc": 1500000,
            "target_range_min": 2000000,
            "target_range_max": 2500000,
            "role_title": "Dev",
            "company_name": "Startup",
            "company_context": "Series B, 200 employees",
        }
        messages = agent.build_messages(state)
        assert "Series B" in messages[0].content

    def test_no_company_context(self):
        agent = CompensationCoachAgent()
        state = {
            "locale": "IN",
            "current_ctc": 1500000,
            "target_range_min": 2000000,
            "target_range_max": 2500000,
            "role_title": "Dev",
            "company_name": "Corp",
        }
        messages = agent.build_messages(state)
        assert "None provided" in messages[0].content


class TestProcessResponse:

    def test_valid_json_with_scripts_and_tips(self):
        agent = CompensationCoachAgent()
        data = {
            "scripts": [
                {
                    "script_text": "Based on my research...",
                    "strategy_name": "anchoring_high",
                    "strategy_explanation": "Sets a high anchor.",
                    "risk_level": "high",
                },
                {
                    "script_text": "I'd prefer to understand...",
                    "strategy_name": "deflecting",
                    "strategy_explanation": "Delays commitment.",
                    "risk_level": "low",
                },
                {
                    "script_text": "My target range is...",
                    "strategy_name": "range_based",
                    "strategy_explanation": "Shows flexibility.",
                    "risk_level": "medium",
                },
            ],
            "general_tips": ["Research before", "Don't give first"],
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})

        scripts = json.loads(result["scripts"])
        tips = json.loads(result["general_tips"])
        assert len(scripts) == 3
        assert scripts[0]["strategy_name"] == "anchoring_high"
        assert len(tips) == 2

    def test_json_array_fallback(self):
        agent = CompensationCoachAgent()
        data = [
            {"script_text": "Script 1", "strategy_name": "range_based",
             "strategy_explanation": "...", "risk_level": "low"},
        ]
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})

        scripts = json.loads(result["scripts"])
        assert len(scripts) == 1

    def test_json_with_markdown_fences(self):
        agent = CompensationCoachAgent()
        data = {
            "scripts": [
                {"script_text": "Test", "strategy_name": "deflecting",
                 "strategy_explanation": "x", "risk_level": "low"},
            ],
            "general_tips": [],
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        response = AIMessage(content=raw)
        result = agent.process_response(response, {})

        scripts = json.loads(result["scripts"])
        assert len(scripts) == 1

    def test_malformed_json_fallback(self):
        agent = CompensationCoachAgent()
        response = AIMessage(content="Here are some tips for negotiation...")
        result = agent.process_response(response, {})

        scripts = json.loads(result["scripts"])
        assert len(scripts) == 1
        assert scripts[0]["strategy_name"] == "general"
        assert "tips for negotiation" in scripts[0]["script_text"]


class TestFullCall:

    async def test_agent_call_returns_scripts(self):
        from src.llm.models import ModelConfig, ProviderName

        agent = CompensationCoachAgent()
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
            "scripts": [
                {"script_text": "Test script", "strategy_name": "anchoring_high",
                 "strategy_explanation": "...", "risk_level": "high"},
            ],
            "general_tips": ["Tip 1"],
        }
        model.ainvoke.return_value = AIMessage(content=json.dumps(data))

        state = {
            "locale": "IN",
            "current_ctc": 1500000,
            "target_range_min": 2000000,
            "target_range_max": 2500000,
            "role_title": "SDE-2",
            "company_name": "Acme",
        }

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, {"configurable": {"user_id": "u1"}})

        scripts = json.loads(result["scripts"])
        assert len(scripts) == 1
        assert scripts[0]["strategy_name"] == "anchoring_high"
