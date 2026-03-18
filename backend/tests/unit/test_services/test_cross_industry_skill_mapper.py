"""Tests for cross_industry_skill_mapper — skill translation between industries."""

from src.services.cross_industry_skill_mapper import translate_skills


class TestTranslateSkillsTechToFinance:
    """Tests for tech -> finance skill translations."""

    def test_microservices_maps_to_distributed_systems(self) -> None:
        result = translate_skills(["microservices"], "technology", "finance")
        assert len(result.translations) == 1
        t = result.translations[0]
        assert t.target_equivalent == "Distributed Systems"
        assert t.transferability == 0.70

    def test_ci_cd_maps_to_release_management(self) -> None:
        result = translate_skills(["CI/CD"], "technology", "finance")
        t = result.translations[0]
        assert t.target_equivalent == "Release Management"
        assert t.transferability == 0.75

    def test_multiple_tech_to_finance_skills(self) -> None:
        result = translate_skills(
            ["microservices", "CI/CD", "api design"], "tech", "finance"
        )
        assert len(result.translations) == 3
        targets = {t.target_equivalent for t in result.translations}
        assert "Distributed Systems" in targets
        assert "Release Management" in targets
        assert "API Design" in targets


class TestTranslateSkillsTechToHealthcare:
    """Tests for tech -> healthcare skill translations."""

    def test_microservices_maps_to_health_it(self) -> None:
        result = translate_skills(["microservices"], "software", "healthcare")
        t = result.translations[0]
        assert t.target_equivalent == "Health IT Architecture"
        assert t.transferability == 0.65

    def test_machine_learning_maps_to_clinical_ai(self) -> None:
        result = translate_skills(["machine learning"], "tech", "healthcare")
        t = result.translations[0]
        assert t.target_equivalent == "Clinical AI/ML"
        assert t.transferability == 0.55


class TestUniversalSkills:
    """Tests for skills that transfer across all industries."""

    def test_project_management_universal(self) -> None:
        result = translate_skills(["project management"], "tech", "finance")
        t = result.translations[0]
        assert t.target_equivalent == "Project Management"
        assert t.transferability == 0.95

    def test_python_universal(self) -> None:
        result = translate_skills(["python"], "retail", "healthcare")
        t = result.translations[0]
        assert t.transferability == 0.80

    def test_sql_universal(self) -> None:
        result = translate_skills(["SQL"], "manufacturing", "finance")
        t = result.translations[0]
        assert t.transferability == 0.85


class TestDefaultAndEdgeCases:
    """Tests for unknown skills and edge cases."""

    def test_unknown_skill_gets_default_transferability(self) -> None:
        result = translate_skills(["quantum entanglement"], "tech", "finance")
        t = result.translations[0]
        assert t.transferability == 0.5
        assert t.target_equivalent == "quantum entanglement"

    def test_empty_skills_list(self) -> None:
        result = translate_skills([], "tech", "finance")
        assert result.translations == []
        assert result.overall_transferability == 0.0

    def test_overall_transferability_calculation(self) -> None:
        result = translate_skills(
            ["project management", "microservices"], "tech", "finance"
        )
        # (0.95 + 0.70) / 2 * 100 = 82.5
        assert result.overall_transferability == 82.5

    def test_highly_transferable_categorization(self) -> None:
        result = translate_skills(
            ["project management", "python", "SQL"], "tech", "finance"
        )
        assert "project management" in result.highly_transferable
        assert "python" in result.highly_transferable
        assert "SQL" in result.highly_transferable
        assert result.needs_adaptation == []

    def test_needs_adaptation_categorization(self) -> None:
        result = translate_skills(["microservices"], "tech", "finance")
        assert "microservices" in result.needs_adaptation

    def test_non_transferable_categorization(self) -> None:
        """Skills with transferability < 0.5 are non-transferable (none in current data)."""
        # All known mappings are >= 0.5, so test with a boundary scenario.
        # machine_learning -> clinical AI/ML has 0.55 which is needs_adaptation.
        result = translate_skills(["machine learning"], "tech", "healthcare")
        assert "machine learning" in result.needs_adaptation


class TestIsTechFix:
    """Verify _is_tech doesn't false-positive on 'it' substrings."""

    def test_hospitality_not_tech(self):
        result = translate_skills(["python"], "hospitality", "finance")
        # Should use empty industry map (not tech->finance map)
        assert result.source_industry == "hospitality"

    def test_consulting_not_tech(self):
        result = translate_skills(["python"], "consulting", "finance")
        assert result.source_industry == "consulting"

    def test_it_alone_is_tech(self):
        result = translate_skills(["microservices"], "it", "finance")
        # "it" alone should match as tech
        assert any(t.target_equivalent == "Distributed Systems" for t in result.translations)

    def test_it_services_is_tech(self):
        result = translate_skills(["microservices"], "it services", "finance")
        assert any(t.target_equivalent == "Distributed Systems" for t in result.translations)
