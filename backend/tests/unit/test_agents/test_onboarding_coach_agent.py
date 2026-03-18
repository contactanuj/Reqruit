"""Tests for OnboardingCoachAgent."""

import json

from langchain_core.messages import AIMessage

from src.agents.onboarding_coach import OnboardingCoachAgent, onboarding_coach_agent
from src.llm.models import TaskType


class TestOnboardingCoachAgentInstantiation:
    def test_singleton_exists(self):
        assert onboarding_coach_agent is not None
        assert isinstance(onboarding_coach_agent, OnboardingCoachAgent)

    def test_task_type(self):
        agent = OnboardingCoachAgent()
        assert agent.task_type == TaskType.ONBOARDING_PLANNING

    def test_name(self):
        agent = OnboardingCoachAgent()
        assert agent.name == "onboarding_coach"

    def test_temperature_override(self):
        agent = OnboardingCoachAgent()
        assert agent._temperature_override == 0.7

    def test_system_prompt_includes_confidentiality(self):
        agent = OnboardingCoachAgent()
        assert "confidential" in agent.system_prompt.lower()
        assert "private" in agent.system_prompt.lower()


class TestBuildMessages:
    def test_includes_situation(self):
        agent = OnboardingCoachAgent()
        state = {"coaching_query": "My manager gives vague feedback"}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "vague feedback" in messages[0].content

    def test_includes_company_and_role(self):
        agent = OnboardingCoachAgent()
        state = {
            "coaching_query": "Help me",
            "company_name": "Acme Corp",
            "role_title": "Senior Engineer",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Acme Corp" in content
        assert "Senior Engineer" in content

    def test_includes_plan_progress(self):
        agent = OnboardingCoachAgent()
        state = {
            "coaching_query": "Stuck",
            "plan": {
                "milestones": [
                    {"title": "A", "completed": True},
                    {"title": "B", "completed": False},
                    {"title": "C", "completed": True},
                ],
            },
        }
        messages = agent.build_messages(state)
        assert "2/3" in messages[0].content

    def test_fallback_with_empty_state(self):
        agent = OnboardingCoachAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "guidance" in messages[0].content.lower()


class TestProcessResponse:
    def test_parses_valid_json(self):
        agent = OnboardingCoachAgent()
        response_data = {
            "whats_happening": "Normal new-hire adjustment",
            "how_to_respond": "Schedule a 1:1 with your manager",
            "conversation_scripts": ["I'd appreciate more specific feedback on..."],
            "when_to_escalate": "If feedback remains vague after 2 attempts",
        }
        response = AIMessage(content=json.dumps(response_data))
        result = agent.process_response(response, {})

        assert "coaching_response" in result
        parsed = json.loads(result["coaching_response"])
        assert parsed["whats_happening"] == "Normal new-hire adjustment"
        assert len(parsed["conversation_scripts"]) == 1

    def test_parses_json_in_markdown_fences(self):
        agent = OnboardingCoachAgent()
        data = {
            "whats_happening": "Context",
            "how_to_respond": "Action",
            "conversation_scripts": ["Script 1"],
            "when_to_escalate": "Red flag",
        }
        response = AIMessage(content=f"```json\n{json.dumps(data)}\n```")
        result = agent.process_response(response, {})
        parsed = json.loads(result["coaching_response"])
        assert parsed["how_to_respond"] == "Action"

    def test_fallback_on_invalid_json(self):
        agent = OnboardingCoachAgent()
        response = AIMessage(content="Here's my advice: just talk to your manager.")
        result = agent.process_response(response, {})

        assert "coaching_response" in result
        parsed = json.loads(result["coaching_response"])
        # Fallback puts raw content in whats_happening
        assert "advice" in parsed["whats_happening"]
        assert parsed["conversation_scripts"] == []
