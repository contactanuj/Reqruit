"""
Tests for NegotiationCoachAgent — recruiter persona and coaching feedback.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.agents.negotiation_coach import NegotiationCoachAgent
from src.llm.models import TaskType


class TestNegotiationCoachConfig:

    def test_name(self):
        agent = NegotiationCoachAgent()
        assert agent.name == "negotiation_coach"

    def test_task_type(self):
        agent = NegotiationCoachAgent()
        assert agent.task_type == TaskType.NEGOTIATION_COACHING

    def test_system_prompt_contains_recruiter_and_coach(self):
        agent = NegotiationCoachAgent()
        assert "RECRUITER" in agent.system_prompt
        assert "COACH" in agent.system_prompt

    def test_system_prompt_locale_rules(self):
        agent = NegotiationCoachAgent()
        assert "India" in agent.system_prompt or "IN" in agent.system_prompt
        assert "US" in agent.system_prompt


class TestBuildMessages:

    def test_first_turn_includes_offer_context(self):
        agent = NegotiationCoachAgent()
        state = {
            "offer_details": {
                "company_name": "Acme Corp",
                "role_title": "SDE-2",
                "total_comp_annual": 2500000,
                "locale_market": "IN",
            },
            "market_data": {},
            "competing_offers": [],
            "user_priorities": {},
            "simulation_transcript": [],
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Acme Corp" in messages[0].content
        assert "SDE-2" in messages[0].content

    def test_subsequent_turn_includes_history(self):
        agent = NegotiationCoachAgent()
        state = {
            "offer_details": {"company_name": "Acme", "role_title": "Dev"},
            "market_data": {},
            "competing_offers": [],
            "user_priorities": {},
            "simulation_transcript": [
                {"role": "recruiter", "content": "We offer 25 LPA."},
                {"role": "user", "content": "I was expecting 30 LPA."},
            ],
            "user_response": "I have competing offers at 28 LPA.",
        }
        messages = agent.build_messages(state)
        assert len(messages) > 1
        # Check user response is included
        contents = " ".join(m.content for m in messages)
        assert "competing offers" in contents

    def test_competing_offers_mentioned(self):
        agent = NegotiationCoachAgent()
        state = {
            "offer_details": {"company_name": "X"},
            "market_data": {},
            "competing_offers": [{"company": "Y", "total": 3000000}],
            "user_priorities": {"target_salary": 3000000},
            "simulation_transcript": [],
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Competing offers: 1" in content


class TestProcessResponse:

    def test_valid_json_response(self):
        agent = NegotiationCoachAgent()
        data = {
            "recruiter_response": "We can offer a 5% bump.",
            "coaching_feedback": "Good use of anchoring.",
            "tactic_detected": "anchoring",
            "turn_number": 2,
            "simulation_complete": False,
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {"simulation_transcript": []})

        assert result["recruiter_response"] == "We can offer a 5% bump."
        assert result["coaching_feedback"] == "Good use of anchoring."
        assert result["tactic_detected"] == "anchoring"
        assert result["turn_number"] == 2
        assert result["simulation_complete"] is False

    def test_json_with_markdown_fences(self):
        agent = NegotiationCoachAgent()
        data = {
            "recruiter_response": "Final offer.",
            "coaching_feedback": "Well negotiated.",
            "tactic_detected": "concession",
            "turn_number": 5,
            "simulation_complete": True,
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        response = AIMessage(content=raw)
        result = agent.process_response(response, {"simulation_transcript": []})

        assert result["recruiter_response"] == "Final offer."
        assert result["simulation_complete"] is True

    def test_malformed_json_fallback(self):
        agent = NegotiationCoachAgent()
        response = AIMessage(content="I can't parse this as JSON")
        result = agent.process_response(response, {"simulation_transcript": [{"x": 1}]})

        assert result["recruiter_response"] == "I can't parse this as JSON"
        assert result["coaching_feedback"] == ""
        assert result["simulation_complete"] is False
        assert result["turn_number"] == 2  # len(transcript) + 1

    async def test_full_call_returns_structured_result(self):
        from src.llm.models import ModelConfig, ProviderName

        agent = NegotiationCoachAgent()
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
            "recruiter_response": "Opening offer is 25 LPA.",
            "coaching_feedback": "",
            "tactic_detected": "",
            "turn_number": 1,
            "simulation_complete": False,
        }
        model.ainvoke.return_value = AIMessage(content=json.dumps(data))

        state = {
            "offer_details": {"company_name": "Test"},
            "market_data": {},
            "competing_offers": [],
            "user_priorities": {},
            "simulation_transcript": [],
        }

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, {"configurable": {"user_id": "u1"}})

        assert result["recruiter_response"] == "Opening offer is 25 LPA."
        assert result["turn_number"] == 1
