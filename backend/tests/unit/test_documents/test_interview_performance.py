"""Tests for the InterviewPerformance document model and QuestionScore embedded model."""

from beanie import PydanticObjectId

from src.db.documents.interview_performance import (
    InterviewPerformance,
    QuestionScore,
)


class TestQuestionScore:
    """Tests for QuestionScore embedded model."""

    def test_create_with_all_fields(self) -> None:
        score = QuestionScore(
            question_text="Tell me about a time you led a team.",
            question_type="behavioral",
            score_relevance=4,
            score_structure=5,
            score_specificity=3,
            score_confidence=4,
            feedback="Good STAR structure but could add more specifics.",
            improvement_suggestion="Quantify the team size and project outcome.",
        )
        assert score.question_text == "Tell me about a time you led a team."
        assert score.question_type == "behavioral"
        assert score.score_relevance == 4
        assert score.score_structure == 5
        assert score.score_specificity == 3
        assert score.score_confidence == 4
        assert "STAR" in score.feedback
        assert score.improvement_suggestion != ""

    def test_defaults(self) -> None:
        score = QuestionScore(question_text="Describe a challenge.")
        assert score.question_type == ""
        assert score.score_relevance == 0
        assert score.score_structure == 0
        assert score.score_specificity == 0
        assert score.score_confidence == 0
        assert score.feedback == ""
        assert score.improvement_suggestion == ""


class TestInterviewPerformance:
    """Tests for InterviewPerformance document."""

    def test_collection_name(self) -> None:
        assert InterviewPerformance.Settings.name == "interview_performances"

    def test_create_with_required_fields(self) -> None:
        user_id = PydanticObjectId()
        perf = InterviewPerformance(user_id=user_id, session_id="abc-123")
        assert perf.user_id == user_id
        assert perf.session_id == "abc-123"
        assert perf.company_name == ""
        assert perf.role_title == ""
        assert perf.difficulty_level == "medium"
        assert perf.question_scores == []
        assert perf.overall_score == 0.0
        assert perf.strengths == []
        assert perf.improvement_areas == []
        assert perf.session_summary == ""

    def test_create_with_all_fields(self) -> None:
        perf = InterviewPerformance(
            user_id=PydanticObjectId(),
            session_id="session-456",
            company_name="Acme Corp",
            role_title="Senior Engineer",
            difficulty_level="hard",
            question_scores=[
                QuestionScore(
                    question_text="Design a distributed cache.",
                    question_type="technical",
                    score_relevance=5,
                    score_structure=4,
                    score_specificity=4,
                    score_confidence=3,
                ),
            ],
            overall_score=4.0,
            strengths=["Technical depth", "Clear communication"],
            improvement_areas=["Confidence under pressure"],
            session_summary="Strong technical session with room for growth.",
        )
        assert perf.company_name == "Acme Corp"
        assert perf.difficulty_level == "hard"
        assert len(perf.question_scores) == 1
        assert perf.question_scores[0].question_type == "technical"
        assert perf.overall_score == 4.0
        assert len(perf.strengths) == 2
        assert len(perf.improvement_areas) == 1

    def test_schema_version_default(self) -> None:
        perf = InterviewPerformance(
            user_id=PydanticObjectId(), session_id="s1"
        )
        assert perf.schema_version == 1

    def test_timestamps_default_to_none(self) -> None:
        perf = InterviewPerformance(
            user_id=PydanticObjectId(), session_id="s1"
        )
        assert perf.created_at is None
        assert perf.updated_at is None
