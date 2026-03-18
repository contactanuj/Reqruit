"""
Unit tests for MockInterviewer and MockInterviewSummarizer agents.

Coverage:
- Agent configuration (name, task_type)
- build_messages constructs correct prompt
- process_response delegates to parser
- parse_interviewer_feedback with well-formatted and malformed input
- parse_summary_feedback with well-formatted and malformed input
"""

from langchain_core.messages import AIMessage

from src.agents.interview_prep import (
    MockInterviewer,
    MockInterviewSummarizer,
    parse_interviewer_feedback,
    parse_summary_feedback,
)
from src.llm.models import TaskType


# ---------------------------------------------------------------------------
# MockInterviewer
# ---------------------------------------------------------------------------


class TestMockInterviewerConfig:
    def test_name(self):
        agent = MockInterviewer()
        assert agent.name == "mock_interviewer"

    def test_task_type(self):
        agent = MockInterviewer()
        assert agent.task_type == TaskType.MOCK_INTERVIEW


class TestMockInterviewerBuildMessages:
    def test_includes_question_and_answer(self):
        agent = MockInterviewer()
        messages = agent.build_messages(
            {"question": "Tell me about a time...", "user_answer": "I once led..."}
        )
        assert len(messages) == 1
        assert "Tell me about a time..." in messages[0].content
        assert "I once led..." in messages[0].content

    def test_handles_empty_state(self):
        agent = MockInterviewer()
        messages = agent.build_messages({})
        assert len(messages) == 1


class TestMockInterviewerProcessResponse:
    def test_delegates_to_parser(self):
        agent = MockInterviewer()
        response = AIMessage(content="Score: 8\nFeedback: Great use of STAR method.")
        result = agent.process_response(response, {})
        assert result["score"] == 8
        assert "STAR" in result["feedback"]


# ---------------------------------------------------------------------------
# parse_interviewer_feedback
# ---------------------------------------------------------------------------


class TestParseInterviewerFeedback:
    def test_well_formatted(self):
        text = "Score: 7\nFeedback: Good answer with clear structure."
        result = parse_interviewer_feedback(text)
        assert result["score"] == 7
        assert result["feedback"] == "Good answer with clear structure."

    def test_score_clamped_high(self):
        text = "Score: 15\nFeedback: Amazing."
        result = parse_interviewer_feedback(text)
        assert result["score"] == 10

    def test_score_clamped_low(self):
        text = "Score: 0\nFeedback: Needs work."
        result = parse_interviewer_feedback(text)
        assert result["score"] == 1

    def test_no_score(self):
        text = "The answer was decent but lacked specifics."
        result = parse_interviewer_feedback(text)
        assert result["score"] is None
        assert "decent" in result["feedback"]

    def test_no_feedback_label(self):
        text = "Score: 6\nSome freeform feedback here."
        result = parse_interviewer_feedback(text)
        assert result["score"] == 6
        # Falls back to full text since no "Feedback:" label
        assert "Score: 6" in result["feedback"]


# ---------------------------------------------------------------------------
# MockInterviewSummarizer
# ---------------------------------------------------------------------------


class TestMockInterviewSummarizerConfig:
    def test_name(self):
        agent = MockInterviewSummarizer()
        assert agent.name == "mock_interview_summarizer"

    def test_task_type(self):
        agent = MockInterviewSummarizer()
        assert agent.task_type == TaskType.MOCK_INTERVIEW


class TestMockInterviewSummarizerBuildMessages:
    def test_includes_transcript(self):
        agent = MockInterviewSummarizer()
        messages = agent.build_messages(
            {"session_transcript": "Q1: Tell me...\nAnswer: I did..."}
        )
        assert len(messages) == 1
        assert "Q1: Tell me..." in messages[0].content


class TestMockInterviewSummarizerProcessResponse:
    def test_delegates_to_parser(self):
        agent = MockInterviewSummarizer()
        response = AIMessage(
            content="Overall Score: 75\nSummary: Good performance overall."
        )
        result = agent.process_response(response, {})
        assert result["overall_score"] == 75
        assert "Good performance" in result["overall_feedback"]


# ---------------------------------------------------------------------------
# parse_summary_feedback
# ---------------------------------------------------------------------------


class TestParseSummaryFeedback:
    def test_well_formatted(self):
        text = "Overall Score: 82\nSummary: Strong showing across all questions."
        result = parse_summary_feedback(text)
        assert result["overall_score"] == 82
        assert "Strong showing" in result["overall_feedback"]

    def test_score_clamped_high(self):
        text = "Overall Score: 150\nSummary: Perfect."
        result = parse_summary_feedback(text)
        assert result["overall_score"] == 100

    def test_score_clamped_low(self):
        text = "Overall Score: 0\nSummary: Needs improvement."
        result = parse_summary_feedback(text)
        assert result["overall_score"] == 0

    def test_no_score(self):
        text = "The candidate showed promise but needs practice."
        result = parse_summary_feedback(text)
        assert result["overall_score"] is None
        assert "promise" in result["overall_feedback"]
