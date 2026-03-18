"""
Tests for enhanced QuestionPredictorAgent — confidence indicator + system_design type.
"""

import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agents.question_predictor import QuestionPredictorAgent


@pytest.fixture()
def agent():
    return QuestionPredictorAgent()


class TestProcessResponseParsing:
    def test_parses_json_with_confidence(self, agent) -> None:
        questions = [
            {
                "question_text": "Design a URL shortener",
                "question_type": "system_design",
                "difficulty": "hard",
                "confidence": "high",
                "suggested_preparation": "Study distributed systems",
            },
            {
                "question_text": "Tell me about a time you led a team",
                "question_type": "behavioral",
                "difficulty": "medium",
                "confidence": "medium",
                "suggested_preparation": "Prepare STAR stories",
            },
        ]
        ai_response = AIMessage(content=json.dumps(questions))
        result = agent.process_response(ai_response, {})
        parsed = json.loads(result["predicted_questions"])

        assert len(parsed) == 2
        assert parsed[0]["confidence"] == "high"
        assert parsed[0]["question_type"] == "system_design"
        assert parsed[1]["confidence"] == "medium"

    def test_handles_non_json_fallback(self, agent) -> None:
        ai_response = AIMessage(
            content="1. Tell me about yourself\n2. Why this company?"
        )
        result = agent.process_response(ai_response, {})

        assert "predicted_questions" in result
        assert "Tell me about yourself" in result["predicted_questions"]

    def test_handles_json_object_not_array(self, agent) -> None:
        ai_response = AIMessage(content='{"questions": []}')
        result = agent.process_response(ai_response, {})

        # Non-array JSON falls through to raw content
        assert "predicted_questions" in result
        assert result["predicted_questions"] == '{"questions": []}'

    def test_preserves_all_fields(self, agent) -> None:
        questions = [
            {
                "question_text": "What is REST?",
                "question_type": "technical",
                "difficulty": "easy",
                "confidence": "high",
                "suggested_preparation": "Review API design",
            },
        ]
        ai_response = AIMessage(content=json.dumps(questions))
        result = agent.process_response(ai_response, {})
        parsed = json.loads(result["predicted_questions"])

        assert parsed[0]["suggested_preparation"] == "Review API design"
        assert parsed[0]["difficulty"] == "easy"


class TestBuildMessages:
    def test_includes_company_and_role(self, agent) -> None:
        state = {
            "company_name": "Google",
            "role_title": "SDE-2",
            "jd_analysis": "Build scalable APIs",
        }
        messages = agent.build_messages(state)

        assert len(messages) == 1
        content = messages[0].content
        assert "Google" in content
        assert "SDE-2" in content
        assert "Build scalable APIs" in content

    def test_includes_locale_context(self, agent) -> None:
        state = {
            "company_name": "TCS",
            "role_title": "SDE",
            "jd_analysis": "",
            "company_research": "IT services leader",
            "locale_context": "Indian campus placement norms",
        }
        messages = agent.build_messages(state)
        content = messages[0].content
        assert "Indian campus placement" in content
        assert "IT services leader" in content


class TestSystemPrompt:
    def test_prompt_includes_system_design(self, agent) -> None:
        assert "system_design" in agent.system_prompt

    def test_prompt_includes_confidence(self, agent) -> None:
        assert "confidence" in agent.system_prompt
