"""Tests for WeeklyReviewAgent — weekly strategy review."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.weekly_review import WeeklyReviewAgent
from src.llm.models import TaskType


class TestWeeklyReviewConfig:
    def test_name(self) -> None:
        agent = WeeklyReviewAgent()
        assert agent.name == "weekly_review"

    def test_task_type(self) -> None:
        agent = WeeklyReviewAgent()
        assert agent.task_type == TaskType.WEEKLY_REVIEW

    def test_system_prompt_mentions_goals(self) -> None:
        agent = WeeklyReviewAgent()
        assert "goals" in agent.system_prompt.lower()
        assert "tactical" in agent.system_prompt.lower()


class TestBuildMessages:
    def test_includes_current_metrics(self) -> None:
        agent = WeeklyReviewAgent()
        state = {"current_metrics": {"applications_count": 10, "xp_earned": 200}}
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "applications_count" in messages[0].content

    def test_includes_previous_metrics(self) -> None:
        agent = WeeklyReviewAgent()
        state = {
            "current_metrics": {"applications_count": 5},
            "previous_metrics": {"applications_count": 8},
        }
        messages = agent.build_messages(state)
        assert "Last week" in messages[0].content

    def test_includes_inflection_warning(self) -> None:
        agent = WeeklyReviewAgent()
        state = {
            "current_metrics": {"applications_count": 5},
            "inflection_warning": "Response rate dropped",
        }
        messages = agent.build_messages(state)
        assert "INFLECTION WARNING" in messages[0].content

    def test_insufficient_data_note(self) -> None:
        agent = WeeklyReviewAgent()
        state = {"current_metrics": {"apps": 2}, "data_driven": False}
        messages = agent.build_messages(state)
        assert "Insufficient data" in messages[0].content

    def test_empty_state(self) -> None:
        agent = WeeklyReviewAgent()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No activity data" in messages[0].content


class TestProcessResponse:
    def test_valid_json_parsed(self) -> None:
        agent = WeeklyReviewAgent()
        data = {
            "summary": "Good week",
            "tactical_adjustments": ["Apply to more startups"],
            "next_week_goals": ["Goal 1", "Goal 2", "Goal 3"],
            "encouragement": "Keep it up!",
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})

        assert result["summary"] == "Good week"
        assert len(result["next_week_goals"]) == 3
        assert len(result["tactical_adjustments"]) == 1

    def test_json_with_markdown_fences(self) -> None:
        agent = WeeklyReviewAgent()
        data = {
            "summary": "Solid progress",
            "tactical_adjustments": [],
            "next_week_goals": ["A", "B", "C"],
            "encouragement": "Nice!",
        }
        raw = f"```json\n{json.dumps(data)}\n```"
        response = AIMessage(content=raw)
        result = agent.process_response(response, {})
        assert result["summary"] == "Solid progress"

    def test_malformed_json_returns_fallback(self) -> None:
        agent = WeeklyReviewAgent()
        response = AIMessage(content="Great week overall, keep pushing!")
        result = agent.process_response(response, {})

        assert "Great week" in result["summary"]
        assert len(result["next_week_goals"]) == 3

    def test_caps_goals_at_3(self) -> None:
        agent = WeeklyReviewAgent()
        data = {
            "summary": "Ok",
            "tactical_adjustments": [],
            "next_week_goals": ["1", "2", "3", "4", "5"],
            "encouragement": "Go!",
        }
        response = AIMessage(content=json.dumps(data))
        result = agent.process_response(response, {})
        assert len(result["next_week_goals"]) == 3


class TestFullCall:
    async def test_agent_call_returns_review(self) -> None:
        from src.llm.models import ModelConfig, ProviderName

        agent = WeeklyReviewAgent()
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
            "summary": "Productive week",
            "tactical_adjustments": ["Focus on networking"],
            "next_week_goals": ["Apply x5", "Network x2", "Mock x1"],
            "encouragement": "You're doing great!",
        }
        model.ainvoke.return_value = AIMessage(content=json.dumps(data))

        state = {"current_metrics": {"applications_count": 10}}

        with patch("src.agents.base.get_model_manager", return_value=manager):
            result = await agent(state, {"configurable": {"user_id": "u1"}})

        assert result["summary"] == "Productive week"
        assert len(result["next_week_goals"]) == 3
