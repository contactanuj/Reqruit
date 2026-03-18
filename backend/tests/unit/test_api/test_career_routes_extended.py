"""Tests for extended /career/* endpoints — vitals, path simulation, signals, and more."""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import get_current_user
from src.services.cross_industry_skill_mapper import SkillTranslationResult, SkillTranslation
from src.services.stepping_stone_pathfinder import SteppingStoneResult
from src.services.gcc_career_ladder import GCCCareerAnalysis, GCCCareerPath


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _override(app, user):
    app.dependency_overrides[get_current_user] = lambda: user


class TestCareerVitals:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "overall_score": 72.5,
            "career_stage": "mid",
            "metrics": [
                {"name": "skill_relevance", "score": 80.0, "trend": "improving", "explanation": "Good"},
            ],
            "drift_indicators": [
                {"category": "skill_gap", "severity": "medium", "description": "Gap", "recommended_action": "Learn"},
            ],
        }

        with (
            patch("src.api.routes.career.career_drift_detector_agent", new_callable=AsyncMock, return_value=agent_result),
            patch("src.api.routes.career.CareerVitalsRepository") as MockRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.create = AsyncMock()

            response = await client.post("/career/vitals", json={
                "role_title": "Senior Engineer",
                "industry": "tech",
                "years_experience": 5,
                "skills": ["python", "fastapi"],
                "career_goals": "Staff Engineer",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 72.5
        assert data["career_stage"] == "mid"
        assert len(data["metrics"]) == 1
        assert len(data["drift_indicators"]) == 1

    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/vitals", json={
            "role_title": "Engineer",
        })
        assert response.status_code in (401, 403)


class TestPathSimulation:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "scenarios": [{"title": "Stay on IC track", "probability": 0.7}],
            "india_insights": {"notice_period": "typical 90 days"},
        }

        with patch("src.api.routes.career.career_path_simulator_agent", new_callable=AsyncMock, return_value=agent_result):
            response = await client.post("/career/path-simulation", json={
                "role_title": "Senior Engineer",
                "industry": "tech",
            })

        assert response.status_code == 200
        data = response.json()
        assert len(data["scenarios"]) == 1
        assert "india_insights" in data


class TestEarlyWarningSignals:
    async def test_200_returns_empty_when_no_vitals(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        with patch("src.api.routes.career.CareerVitalsRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_latest = AsyncMock(return_value=None)

            response = await client.get("/career/signals")

        assert response.status_code == 200
        assert response.json() == []


class TestLearningPath:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "learning_paths": [{"skill": "Kubernetes", "resources": []}],
            "total_estimated_hours": 120,
            "recommended_schedule": "2 hours/day",
        }

        with patch("src.api.routes.career.learning_path_architect_agent", new_callable=AsyncMock, return_value=agent_result):
            response = await client.post("/career/learning-path", json={
                "current_skills": ["python"],
                "target_skills": ["kubernetes"],
                "role_title": "DevOps Engineer",
            })

        assert response.status_code == 200
        data = response.json()
        assert len(data["learning_paths"]) == 1
        assert data["total_estimated_hours"] == 120


class TestNarrative:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "career_arc": {"theme": "builder"},
            "stories": [{"title": "Led migration"}],
            "positioning_statement": "A builder of scalable systems.",
            "elevator_pitch": "I help teams ship faster.",
        }

        with patch("src.api.routes.career.story_arc_builder_agent", new_callable=AsyncMock, return_value=agent_result):
            response = await client.post("/career/narrative", json={
                "experiences": [{"company": "Acme", "role": "Engineer"}],
                "achievements": ["Shipped v2"],
                "role_title": "Senior Engineer",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["career_arc"]["theme"] == "builder"
        assert data["positioning_statement"] == "A builder of scalable systems."


class TestSkillTranslate:
    async def test_200_deterministic(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_result = SkillTranslationResult(
            source_industry="tech",
            target_industry="finance",
            translations=[
                SkillTranslation(
                    source_skill="python",
                    target_equivalent="Python",
                    transferability=0.80,
                    context_shift="Language transfers",
                    gap_to_close="Learn domain libraries",
                ),
                SkillTranslation(
                    source_skill="microservices",
                    target_equivalent="Distributed Systems",
                    transferability=0.70,
                    context_shift="Similar architecture",
                    gap_to_close="Learn financial regulations",
                ),
            ],
            highly_transferable=["python"],
            needs_adaptation=["microservices"],
            overall_transferability=75.0,
        )

        with patch("src.api.routes.career.translate_skills", return_value=mock_result):
            response = await client.post("/career/skill-translate", json={
                "skills": ["python", "microservices"],
                "source_industry": "tech",
                "target_industry": "finance",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["source_industry"] == "tech"
        assert data["target_industry"] == "finance"
        assert len(data["translations"]) == 2


class TestBridgeRoles:
    async def test_200_deterministic(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_result = SteppingStoneResult(
            current_role="Backend Developer",
            target_role="ML Engineer",
            direct_transition_feasibility=40.0,
            bridge_roles=[],
            skills_to_acquire=["machine learning"],
            estimated_timeline_months=18,
            recommended_path="Via Data Engineer role",
        )

        with patch("src.api.routes.career.find_bridge_roles", return_value=mock_result):
            response = await client.post("/career/bridge-roles", json={
                "current_role": "Backend Developer",
                "target_role": "ML Engineer",
                "current_skills": ["python", "sql"],
            })

        assert response.status_code == 200
        data = response.json()
        assert data["current_role"] == "Backend Developer"
        assert data["target_role"] == "ML Engineer"
        assert "bridge_roles" in data


class TestCertificationROI:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "certifications": [{"name": "AWS SAA", "roi_score": 85}],
            "top_recommendation": "AWS Solutions Architect Associate",
            "locale_insights": "High demand in India GCCs",
        }

        with patch("src.api.routes.career.certification_roi_ranker_agent", new_callable=AsyncMock, return_value=agent_result):
            response = await client.post("/career/certification-roi", json={
                "role_title": "Cloud Engineer",
                "skills": ["python", "docker"],
                "career_goals": "Cloud Architect",
                "locale": "IN",
            })

        assert response.status_code == 200
        data = response.json()
        assert len(data["certifications"]) == 1
        assert data["top_recommendation"] == "AWS Solutions Architect Associate"


class TestServiceExitPlan:
    async def test_200_on_success(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        agent_result = {
            "readiness_score": 65,
            "skill_gaps": ["system design"],
            "resume_strategy": {"focus": "product impact"},
            "interview_prep": {"rounds": 4},
            "target_companies": {"tier1": ["Google"]},
            "timeline": [{"month": 1, "action": "Start prep"}],
            "compensation_insights": {"expected_hike": "40-80%"},
            "notice_period_strategy": "Negotiate buyout",
        }

        with patch("src.api.routes.career.service_exit_planner_agent", new_callable=AsyncMock, return_value=agent_result):
            response = await client.post("/career/service-exit-plan", json={
                "current_company": "TCS",
                "company_type": "service",
                "role_title": "Senior Developer",
                "years_experience": 5,
                "skills": ["java", "spring"],
            })

        assert response.status_code == 200
        data = response.json()
        assert data["readiness_score"] == 65
        assert "skill_gaps" in data


class TestGCCCareer:
    async def test_200_deterministic(self, client: AsyncClient) -> None:
        user = _make_user()
        _override(client.app, user)

        mock_result = GCCCareerAnalysis(
            current_level="IC2",
            recommended_next_level="IC3",
            ic_path=GCCCareerPath(track="individual_contributor", levels=[], transition_points=[]),
            management_path=GCCCareerPath(track="management", levels=[], transition_points=[]),
            gcc_insights=[],
            growth_recommendations=["Focus on system design"],
        )

        with patch("src.api.routes.career.analyze_gcc_career", return_value=mock_result):
            response = await client.post("/career/gcc-career", json={
                "current_role": "Software Engineer",
                "years_experience": 3,
                "target_track": "individual_contributor",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["current_level"] == "IC2"
        assert data["recommended_next_level"] == "IC3"
        assert "ic_path" in data
        assert "management_path" in data


class TestVitalsErrorHandling:
    async def test_malformed_metrics_handled_gracefully(self, client: AsyncClient) -> None:
        """H4: malformed LLM output should not cause 500."""
        user = _make_user()
        _override(client.app, user)

        # Agent returns metrics with invalid shape (missing required fields)
        agent_result = {
            "overall_score": 60.0,
            "career_stage": "mid",
            "metrics": [
                {"name": "skill_relevance", "score": 80.0, "trend": "stable", "explanation": "OK"},
                {"bad_key": "no_name_field"},  # malformed — should be skipped
            ],
            "drift_indicators": [
                {"not_a_category": True},  # malformed — should be skipped
            ],
        }

        with (
            patch("src.api.routes.career.career_drift_detector_agent", new_callable=AsyncMock, return_value=agent_result),
            patch("src.api.routes.career.CareerVitalsRepository") as MockRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.create = AsyncMock()

            response = await client.post("/career/vitals", json={
                "role_title": "Engineer",
            })

        assert response.status_code == 200
        data = response.json()
        # Only the valid metric should be present, malformed ones skipped
        assert len(data["metrics"]) == 1
        assert data["metrics"][0]["name"] == "skill_relevance"
        assert len(data["drift_indicators"]) == 0


class TestPathSimulationAuth:
    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/path-simulation", json={"role_title": "Engineer"})
        assert response.status_code in (401, 403)


class TestLearningPathAuth:
    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/learning-path", json={})
        assert response.status_code in (401, 403)


class TestNarrativeAuth:
    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/narrative", json={})
        assert response.status_code in (401, 403)


class TestServiceExitAuth:
    async def test_401_without_auth(self, client: AsyncClient) -> None:
        response = await client.post("/career/service-exit-plan", json={})
        assert response.status_code in (401, 403)
