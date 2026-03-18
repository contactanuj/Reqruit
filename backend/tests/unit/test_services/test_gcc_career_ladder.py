"""Tests for gcc_career_ladder — GCC career progression analysis."""

from src.services.gcc_career_ladder import (
    _determine_level,
    _generate_recommendations,
    _get_next_level,
    analyze_gcc_career,
    get_compensation_range,
    get_gcc_level_details,
)


class TestDetermineLevel:
    """Tests for _determine_level based on experience and track."""

    def test_ic_track_0_years(self) -> None:
        assert _determine_level(0, "individual_contributor") == "IC1"

    def test_ic_track_1_year(self) -> None:
        assert _determine_level(1.5, "individual_contributor") == "IC1"

    def test_ic_track_3_years(self) -> None:
        assert _determine_level(3, "individual_contributor") == "IC2"

    def test_ic_track_6_years(self) -> None:
        assert _determine_level(6, "individual_contributor") == "IC3"

    def test_ic_track_10_years(self) -> None:
        assert _determine_level(10, "individual_contributor") == "IC4"

    def test_management_track_3_years_not_ready(self) -> None:
        assert _determine_level(3, "management") == "IC2"

    def test_management_track_5_years(self) -> None:
        assert _determine_level(5, "management") == "M1"

    def test_management_track_9_years(self) -> None:
        assert _determine_level(9, "management") == "M2"

    def test_management_track_15_years(self) -> None:
        assert _determine_level(15, "management") == "M3"


class TestGetNextLevel:
    """Tests for _get_next_level progression."""

    def test_ic1_to_ic2(self) -> None:
        assert _get_next_level("IC1", "individual_contributor") == "IC2"

    def test_ic4_stays_ic4(self) -> None:
        assert _get_next_level("IC4", "individual_contributor") == "IC4"

    def test_m1_to_m2(self) -> None:
        assert _get_next_level("M1", "management") == "M2"

    def test_m3_stays_m3(self) -> None:
        assert _get_next_level("M3", "management") == "M3"

    def test_ic2_management_track_goes_to_m1(self) -> None:
        assert _get_next_level("IC2", "management") == "M1"


class TestGetGCCLevelDetails:
    """Tests for get_gcc_level_details lookup."""

    def test_known_ic_level(self) -> None:
        details = get_gcc_level_details("IC2")
        assert details is not None
        assert details.title == "Senior Software Engineer"
        assert details.level == "IC2"

    def test_known_management_level(self) -> None:
        details = get_gcc_level_details("M1")
        assert details is not None
        assert details.title == "Engineering Manager"

    def test_unknown_level_returns_none(self) -> None:
        assert get_gcc_level_details("IC99") is None

    def test_case_insensitive_lookup(self) -> None:
        assert get_gcc_level_details("ic3") is not None
        assert get_gcc_level_details("m2") is not None


class TestGetCompensationRange:
    """Tests for get_compensation_range."""

    def test_known_level_returns_range(self) -> None:
        comp = get_compensation_range("IC1")
        assert "LPA" in comp

    def test_unknown_level_returns_not_available(self) -> None:
        assert get_compensation_range("XYZ") == "Not available"


class TestAnalyzeGCCCareer:
    """Tests for analyze_gcc_career end-to-end."""

    def test_ic_track_junior(self) -> None:
        result = analyze_gcc_career("Software Engineer", 1.0)
        assert result.current_level == "IC1"
        assert result.recommended_next_level == "IC2"
        assert len(result.ic_path.levels) == 4
        assert len(result.management_path.levels) == 3

    def test_ic_track_senior(self) -> None:
        result = analyze_gcc_career("Staff Engineer", 6.0)
        assert result.current_level == "IC3"
        assert result.recommended_next_level == "IC4"

    def test_management_track(self) -> None:
        result = analyze_gcc_career("Engineering Manager", 8.0, target_track="management")
        assert result.current_level == "M2"
        assert result.recommended_next_level == "M3"

    def test_gcc_insights_populated(self) -> None:
        result = analyze_gcc_career("Developer", 2.0)
        assert len(result.gcc_insights) == 4
        types = {i.gcc_type for i in result.gcc_insights}
        assert "faang" in types
        assert "financial" in types


class TestGenerateRecommendations:
    """Tests for _generate_recommendations."""

    def test_at_top_level_mentions_mentoring(self) -> None:
        recs = _generate_recommendations("IC4", "IC4", 10.0, "individual_contributor")
        assert any("mentoring" in r.lower() or "thought leadership" in r.lower() for r in recs)

    def test_mid_level_includes_skills(self) -> None:
        recs = _generate_recommendations("IC2", "IC3", 3.0, "individual_contributor")
        assert any("skills" in r.lower() for r in recs)

    def test_junior_includes_portfolio(self) -> None:
        recs = _generate_recommendations("IC1", "IC2", 1.0, "individual_contributor")
        assert any("portfolio" in r.lower() for r in recs)

    def test_experienced_ic_mentions_management_option(self) -> None:
        recs = _generate_recommendations("IC3", "IC4", 6.0, "individual_contributor")
        assert any("management" in r.lower() for r in recs)
