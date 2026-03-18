"""Tests for stepping_stone_pathfinder — bridge role identification."""

from src.services.stepping_stone_pathfinder import find_bridge_roles


class TestFindBridgeRolesBackendToML:
    """Tests for backend -> ML engineer transitions."""

    def test_returns_bridge_roles(self) -> None:
        result = find_bridge_roles("Backend Developer", "ML Engineer")
        assert len(result.bridge_roles) == 2
        titles = [b.title for b in result.bridge_roles]
        assert "Data Engineer" in titles
        assert "ML Platform Engineer" in titles

    def test_feasibility_with_bridges(self) -> None:
        result = find_bridge_roles("Backend Developer", "ML Engineer")
        # 2 bridges -> feasibility = max(30, 100 - 2*20) = 60
        assert result.direct_transition_feasibility == 60.0

    def test_skills_to_acquire_populated(self) -> None:
        result = find_bridge_roles("Backend Developer", "ML Engineer")
        assert len(result.skills_to_acquire) > 0
        assert "data pipelines" in result.skills_to_acquire


class TestFindBridgeRolesBackendToManager:
    """Tests for backend -> engineering manager transitions."""

    def test_returns_tech_lead_bridge(self) -> None:
        result = find_bridge_roles("Backend Developer", "Engineering Manager")
        titles = [b.title for b in result.bridge_roles]
        assert "Tech Lead" in titles

    def test_recommended_path_suggests_bridge(self) -> None:
        result = find_bridge_roles("Backend Developer", "Engineering Manager")
        assert "Tech Lead" in result.recommended_path

    def test_timeline_from_first_bridge(self) -> None:
        result = find_bridge_roles("Backend Developer", "Engineering Manager")
        assert result.estimated_timeline_months == 18


class TestFindBridgeRolesServiceToProduct:
    """Tests for service company -> product company transitions."""

    def test_consultant_to_product_returns_bridges(self) -> None:
        result = find_bridge_roles("Consultant at TCS", "Product Engineer")
        assert len(result.bridge_roles) == 2
        titles = [b.title for b in result.bridge_roles]
        assert "Startup Engineer" in titles


class TestSameCategoryTransition:
    """Tests when current and target map to the same category."""

    def test_same_category_high_feasibility(self) -> None:
        result = find_bridge_roles("Backend Engineer", "API Developer")
        assert result.direct_transition_feasibility == 90.0
        assert result.bridge_roles == []

    def test_same_category_direct_recommendation(self) -> None:
        result = find_bridge_roles("Backend Engineer", "API Developer")
        assert "Direct transition" in result.recommended_path

    def test_same_category_short_timeline(self) -> None:
        result = find_bridge_roles("Backend Engineer", "API Developer")
        assert result.estimated_timeline_months == 6


class TestUnknownRoles:
    """Tests for roles that don't match any known category."""

    def test_unknown_role_defaults_to_ic(self) -> None:
        result = find_bridge_roles("Astronaut", "Mars Colonist")
        # Both default to individual_contributor -> same category
        assert result.direct_transition_feasibility == 90.0

    def test_unknown_to_known_uses_default_bridges(self) -> None:
        # Unknown defaults to individual_contributor, target is product_manager
        result = find_bridge_roles("Astronaut", "Product Manager")
        assert len(result.bridge_roles) >= 1


class TestCurrentSkillsFiltering:
    """Tests that current_skills removes already-held skills from skills_to_acquire."""

    def test_current_skills_excluded(self) -> None:
        """current_skills are lowercased before subtraction from the set."""
        result_without = find_bridge_roles("Backend Developer", "ML Engineer")
        result_with = find_bridge_roles(
            "Backend Developer",
            "ML Engineer",
            current_skills=["data pipelines", "big data tools"],
        )
        assert "data pipelines" not in result_with.skills_to_acquire
        assert "big data tools" not in result_with.skills_to_acquire
        assert len(result_with.skills_to_acquire) < len(result_without.skills_to_acquire)

    def test_no_current_skills_all_included(self) -> None:
        result = find_bridge_roles("Backend Developer", "ML Engineer")
        assert "data pipelines" in result.skills_to_acquire


class TestSkillSubtractionCaseInsensitive:
    """Verify skill subtraction works case-insensitively after M5 fix."""

    def test_uppercase_skills_subtracted(self):
        result = find_bridge_roles("backend developer", "ml engineer", current_skills=["ETL", "data pipelines"])
        # ETL and data pipelines should be removed even though bridge roles list them in mixed case
        assert "etl" not in [s.lower() for s in result.skills_to_acquire]
        assert "data pipelines" not in [s.lower() for s in result.skills_to_acquire]

    def test_mixed_case_skills_subtracted(self):
        result = find_bridge_roles("backend developer", "ml engineer", current_skills=["mlops"])
        assert "mlops" not in [s.lower() for s in result.skills_to_acquire]
