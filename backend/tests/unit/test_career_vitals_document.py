"""Tests for the CareerVitals document model and embedded models."""

from beanie import PydanticObjectId

from src.db.documents.career_vitals import CareerVitals, DriftIndicator, HealthMetric


class TestHealthMetric:
    """Tests for the HealthMetric embedded model."""

    def test_create_with_all_fields(self) -> None:
        metric = HealthMetric(
            name="skill_relevance",
            score=85.0,
            trend="improving",
            explanation="Skills are well-aligned with market demand.",
        )
        assert metric.name == "skill_relevance"
        assert metric.score == 85.0
        assert metric.trend == "improving"
        assert metric.explanation == "Skills are well-aligned with market demand."

    def test_defaults(self) -> None:
        metric = HealthMetric(name="market_demand")
        assert metric.score == 0.0
        assert metric.trend == "stable"
        assert metric.explanation == ""


class TestDriftIndicator:
    """Tests for the DriftIndicator embedded model."""

    def test_create_with_all_fields(self) -> None:
        indicator = DriftIndicator(
            category="skill_gap",
            severity="high",
            description="Cloud skills falling behind market requirements.",
            recommended_action="Complete AWS Solutions Architect certification.",
        )
        assert indicator.category == "skill_gap"
        assert indicator.severity == "high"
        assert indicator.description == "Cloud skills falling behind market requirements."
        assert indicator.recommended_action == "Complete AWS Solutions Architect certification."

    def test_defaults(self) -> None:
        indicator = DriftIndicator(category="stagnation")
        assert indicator.severity == "low"
        assert indicator.description == ""
        assert indicator.recommended_action == ""


class TestCareerVitals:
    """Tests for the CareerVitals document model."""

    def test_create_with_required_fields(self) -> None:
        vitals = CareerVitals(
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        )
        assert str(vitals.user_id) == "aaaaaaaaaaaaaaaaaaaaaaaa"

    def test_default_values(self) -> None:
        vitals = CareerVitals(
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        )
        assert vitals.metrics == []
        assert vitals.drift_indicators == []
        assert vitals.overall_score == 0.0
        assert vitals.career_stage == ""
        assert vitals.industry == ""
        assert vitals.role_title == ""
        assert vitals.years_experience == 0.0
        assert vitals.locale == ""
        assert vitals.assessment_date is None

    def test_settings_name(self) -> None:
        assert CareerVitals.Settings.name == "career_vitals"
