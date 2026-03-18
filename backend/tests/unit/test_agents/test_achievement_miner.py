"""Tests for AchievementMiner agent."""

from langchain_core.messages import HumanMessage

from src.agents.achievement_miner import AchievementMiner
from src.llm.models import TaskType


class TestAchievementMiner:
    def test_name(self) -> None:
        agent = AchievementMiner()
        assert agent.name == "achievement_miner"

    def test_task_type(self) -> None:
        agent = AchievementMiner()
        assert agent.task_type == TaskType.ACHIEVEMENT_MINING

    def test_has_system_prompt(self) -> None:
        agent = AchievementMiner()
        assert "achievement" in agent.system_prompt.lower()

    def test_build_messages_with_resume(self) -> None:
        agent = AchievementMiner()
        state = {
            "resume_text": "John Doe, Senior Engineer at Acme Corp. Led migration to microservices.",
            "work_history": "",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "John Doe" in messages[0].content

    def test_build_messages_with_existing_achievements(self) -> None:
        agent = AchievementMiner()
        state = {
            "resume_text": "Built scalable APIs",
            "existing_achievements": [{"title": "Already found"}],
        }
        messages = agent.build_messages(state)
        assert "Already found" in messages[0].content

    def test_build_messages_empty(self) -> None:
        agent = AchievementMiner()
        messages = agent.build_messages({})
        assert len(messages) == 1
        assert "No work history provided" in messages[0].content

    def test_process_response(self) -> None:
        agent = AchievementMiner()

        class MockResponse:
            content = '[{"title": "Led migration"}]'

        result = agent.process_response(MockResponse(), {})
        assert result == {"mined_achievements": '[{"title": "Led migration"}]'}
