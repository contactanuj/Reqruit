"""
Tests for the Naukri keyword optimizer.

Verifies keyword extraction from JD analysis, presence detection,
coverage calculation, and suggestion generation.
"""

import json

from src.workflows.formatters.keyword_optimizer import (
    KeywordReport,
    extract_jd_keywords,
    optimize_for_naukri,
)


# ---------------------------------------------------------------------------
# extract_jd_keywords
# ---------------------------------------------------------------------------


class TestExtractJDKeywords:
    def test_extracts_required_and_preferred(self) -> None:
        jd = json.dumps({
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker", "Kubernetes"],
        })
        keywords = extract_jd_keywords(jd)
        assert keywords == ["Python", "FastAPI", "Docker", "Kubernetes"]

    def test_only_required(self) -> None:
        jd = json.dumps({"required_skills": ["Go", "gRPC"]})
        keywords = extract_jd_keywords(jd)
        assert keywords == ["Go", "gRPC"]

    def test_invalid_json_returns_empty(self) -> None:
        assert extract_jd_keywords("not json") == []

    def test_empty_string_returns_empty(self) -> None:
        assert extract_jd_keywords("") == []

    def test_none_returns_empty(self) -> None:
        assert extract_jd_keywords(None) == []


# ---------------------------------------------------------------------------
# optimize_for_naukri
# ---------------------------------------------------------------------------


class TestOptimizeForNaukri:
    def test_all_keywords_present(self) -> None:
        keywords = ["Python", "FastAPI", "MongoDB"]
        resume = "Experienced Python developer with FastAPI and MongoDB expertise"
        report = optimize_for_naukri(keywords, resume)
        assert report.coverage_pct == 100.0
        assert len(report.missing_keywords) == 0
        assert len(report.present_keywords) == 3

    def test_partial_coverage(self) -> None:
        keywords = ["Python", "FastAPI", "Kubernetes", "Terraform"]
        resume = "Python developer with FastAPI experience"
        report = optimize_for_naukri(keywords, resume)
        assert report.coverage_pct == 50.0
        assert "Python" in report.present_keywords
        assert "Kubernetes" in report.missing_keywords
        assert len(report.suggestions) == 2

    def test_case_insensitive(self) -> None:
        keywords = ["python", "FASTAPI"]
        resume = "Python and FastAPI developer"
        report = optimize_for_naukri(keywords, resume)
        assert report.coverage_pct == 100.0

    def test_empty_resume(self) -> None:
        keywords = ["Python", "FastAPI"]
        report = optimize_for_naukri(keywords, "")
        assert report.coverage_pct == 0.0
        assert len(report.missing_keywords) == 2

    def test_empty_keywords(self) -> None:
        report = optimize_for_naukri([], "Some resume text")
        assert report.coverage_pct == 0.0
        assert len(report.present_keywords) == 0
        assert len(report.missing_keywords) == 0

    def test_limits_to_top_10(self) -> None:
        keywords = [f"skill_{i}" for i in range(15)]
        resume = "skill_0 skill_1 skill_2 skill_3 skill_4 skill_5 skill_6 skill_7 skill_8 skill_9 skill_10"
        report = optimize_for_naukri(keywords, resume)
        # Only top 10 evaluated
        assert len(report.present_keywords) + len(report.missing_keywords) == 10

    def test_suggestions_format(self) -> None:
        keywords = ["React", "Vue"]
        resume = "React developer"
        report = optimize_for_naukri(keywords, resume)
        assert len(report.suggestions) == 1
        assert "Vue" in report.suggestions[0]
        assert "Consider adding" in report.suggestions[0]
