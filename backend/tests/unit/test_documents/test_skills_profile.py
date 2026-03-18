"""Tests for the SkillsProfile document model and its embedded sub-models."""

from beanie import PydanticObjectId

from src.db.documents.skills_profile import (
    Achievement,
    FitScore,
    Skill,
    SkillsProfile,
)


class TestSkill:
    """Tests for Skill embedded model."""

    def test_create_with_all_fields(self) -> None:
        skill = Skill(
            name="Python",
            category="Programming Language",
            proficiency="EXPERT",
            years_experience=8.0,
            source="resume",
            last_used="2025",
            confidence=0.95,
        )
        assert skill.name == "Python"
        assert skill.category == "Programming Language"
        assert skill.proficiency == "EXPERT"
        assert skill.years_experience == 8.0
        assert skill.source == "resume"
        assert skill.last_used == "2025"
        assert skill.confidence == 0.95

    def test_defaults(self) -> None:
        skill = Skill(name="Go")
        assert skill.category == ""
        assert skill.proficiency == "INTERMEDIATE"
        assert skill.years_experience == 0.0
        assert skill.source == ""
        assert skill.last_used == ""
        assert skill.confidence == 0.0

    def test_proficiency_levels(self) -> None:
        for level in ("BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"):
            skill = Skill(name="Test", proficiency=level)
            assert skill.proficiency == level


class TestAchievement:
    """Tests for Achievement embedded model."""

    def test_create_with_all_fields(self) -> None:
        achievement = Achievement(
            title="Reduced API latency",
            description="Optimized database queries and added caching",
            impact="Reduced p99 latency by 40%",
            skills_demonstrated=["Python", "Redis", "PostgreSQL"],
            context="Senior Engineer at Acme Corp",
            source="mined",
        )
        assert achievement.title == "Reduced API latency"
        assert achievement.impact == "Reduced p99 latency by 40%"
        assert len(achievement.skills_demonstrated) == 3
        assert achievement.source == "mined"

    def test_defaults(self) -> None:
        achievement = Achievement(title="Led migration")
        assert achievement.description == ""
        assert achievement.impact == ""
        assert achievement.skills_demonstrated == []
        assert achievement.context == ""
        assert achievement.source == ""


class TestFitScore:
    """Tests for FitScore embedded model."""

    def test_create_with_all_fields(self) -> None:
        fit = FitScore(
            overall=78.5,
            skills_match=85.0,
            experience_match=70.0,
            matching_skills=["Python", "FastAPI"],
            missing_skills=["Kubernetes"],
            bonus_skills=["Go"],
            explanation="Strong skills match but missing K8s experience.",
        )
        assert fit.overall == 78.5
        assert fit.skills_match == 85.0
        assert len(fit.matching_skills) == 2
        assert len(fit.missing_skills) == 1
        assert len(fit.bonus_skills) == 1

    def test_defaults(self) -> None:
        fit = FitScore()
        assert fit.overall == 0.0
        assert fit.skills_match == 0.0
        assert fit.experience_match == 0.0
        assert fit.matching_skills == []
        assert fit.missing_skills == []
        assert fit.bonus_skills == []
        assert fit.explanation == ""


class TestSkillsProfile:
    """Tests for SkillsProfile document."""

    def test_collection_name(self) -> None:
        assert SkillsProfile.Settings.name == "skills_profiles"

    def test_create_with_user_id(self) -> None:
        user_id = PydanticObjectId()
        profile = SkillsProfile(user_id=user_id)
        assert profile.user_id == user_id
        assert profile.skills == []
        assert profile.achievements == []
        assert profile.summary == ""
        assert profile.analysis_version == 0

    def test_create_with_skills_and_achievements(self) -> None:
        profile = SkillsProfile(
            user_id=PydanticObjectId(),
            skills=[
                Skill(name="Python", proficiency="EXPERT"),
                Skill(name="FastAPI", proficiency="ADVANCED"),
            ],
            achievements=[
                Achievement(title="Built RAG pipeline", impact="3x search accuracy"),
            ],
            summary="Senior backend engineer with strong Python skills.",
            analysis_version=2,
        )
        assert len(profile.skills) == 2
        assert len(profile.achievements) == 1
        assert profile.analysis_version == 2
        assert "Python" in profile.summary

    def test_schema_version_default(self) -> None:
        profile = SkillsProfile(user_id=PydanticObjectId())
        assert profile.schema_version == 1

    def test_timestamps_default_to_none(self) -> None:
        profile = SkillsProfile(user_id=PydanticObjectId())
        assert profile.created_at is None
        assert profile.updated_at is None
