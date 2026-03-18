"""
Tests for BehavioralQuestionGenerator agent.

Verifies agent configuration, message construction, response parsing,
and fallback behavior for malformed LLM output.
"""

from langchain_core.messages import AIMessage

from src.agents.interview_prep import BehavioralQuestionGenerator, parse_questions
from src.llm.models import TaskType


class TestBehavioralQuestionGenerator:

    def test_task_type(self):
        agent = BehavioralQuestionGenerator()
        assert agent.task_type == TaskType.INTERVIEW_PREP

    def test_name(self):
        agent = BehavioralQuestionGenerator()
        assert agent.name == "behavioral_question_generator"

    def test_build_messages_includes_job_info(self):
        agent = BehavioralQuestionGenerator()
        state = {
            "role_title": "Senior Engineer",
            "job_description": "Build scalable systems with Python",
        }
        messages = agent.build_messages(state)
        assert len(messages) == 1
        assert "Senior Engineer" in messages[0].content
        assert "Build scalable systems with Python" in messages[0].content

    def test_build_messages_handles_missing_fields(self):
        agent = BehavioralQuestionGenerator()
        messages = agent.build_messages({})
        assert len(messages) == 1

    def test_process_response_returns_generated_questions(self):
        agent = BehavioralQuestionGenerator()
        response = AIMessage(
            content=(
                "1. Question: Tell me about a time you led a team.\n"
                "   Angle: Leadership under pressure\n\n"
                "2. Question: Describe a debugging scenario.\n"
                "   Angle: Technical problem-solving\n"
            )
        )
        result = agent.process_response(response, {})
        assert "generated_questions" in result
        assert len(result["generated_questions"]) == 2
        assert result["generated_questions"][0]["suggested_angle"] == "Leadership under pressure"


class TestParseQuestions:

    def test_parses_well_formatted_output(self):
        text = (
            "1. Question: Tell me about a time you led a migration.\n"
            "   Angle: Leadership, technical decision-making\n\n"
            "2. Question: Describe a conflict with a team member.\n"
            "   Angle: Conflict resolution\n"
        )
        questions = parse_questions(text)
        assert len(questions) == 2
        assert questions[0]["question"] == "Tell me about a time you led a migration."
        assert questions[0]["suggested_angle"] == "Leadership, technical decision-making"
        assert questions[1]["question"] == "Describe a conflict with a team member."

    def test_fallback_on_malformed_output(self):
        text = "Tell me about leadership\nDescribe a technical challenge"
        questions = parse_questions(text)
        assert len(questions) == 2
        assert questions[0]["question"] == "Tell me about leadership"
        assert questions[0]["suggested_angle"] == "General behavioral competency"

    def test_empty_input(self):
        assert parse_questions("") == []
        assert parse_questions("   ") == []

    def test_handles_missing_angle(self):
        text = "1. Question: Tell me about a challenge.\n\n2. Question: Describe teamwork.\n"
        questions = parse_questions(text)
        assert len(questions) == 2
        assert questions[0]["suggested_angle"] == "General behavioral competency"
