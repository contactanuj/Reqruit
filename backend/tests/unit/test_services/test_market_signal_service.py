"""Tests for market_signal_service — signal classification and scoring."""

from src.services.market_signal_service import (
    classify_signal,
    detect_disruptions,
    predict_company_trajectory,
    score_signal_relevance,
)


class TestClassifySignal:
    """Tests for classify_signal keyword-based classification."""

    def test_layoff_keyword_classified_critical(self) -> None:
        result = classify_signal("Company layoffs announced", "Mass layoff of 500 employees")
        assert result.signal_type == "layoff_alert"
        assert result.severity == "critical"

    def test_hiring_keyword_classified_info(self) -> None:
        result = classify_signal("Hiring spree", "Company is recruiting 200 engineers")
        assert result.signal_type == "hiring_trend"
        assert result.severity == "info"

    def test_compensation_keyword_classified_warning(self) -> None:
        result = classify_signal("Salary adjustments", "Company-wide compensation review")
        assert result.signal_type == "compensation_shift"
        assert result.severity == "warning"

    def test_disruption_keyword_classified_warning(self) -> None:
        result = classify_signal("AI disruption", "Automation transforming the industry")
        assert result.signal_type == "disruption"
        assert result.severity == "warning"

    def test_unrecognized_defaults_to_hiring_info(self) -> None:
        result = classify_signal("Quarterly earnings report", "Revenue grew 10%")
        assert result.signal_type == "hiring_trend"
        assert result.severity == "info"

    def test_industry_and_region_boost_confidence(self) -> None:
        base = classify_signal("Hiring", "Talent acquisition", industry="", region="")
        with_industry = classify_signal("Hiring", "Talent acquisition", industry="tech", region="")
        with_both = classify_signal("Hiring", "Talent acquisition", industry="tech", region="US")
        assert with_industry.confidence > base.confidence
        assert with_both.confidence > with_industry.confidence

    def test_long_description_boosts_confidence(self) -> None:
        short = classify_signal("Layoffs", "Brief.", industry="tech")
        long_desc = "A" * 101
        long = classify_signal("Layoffs", long_desc, industry="tech")
        assert long.confidence > short.confidence


class TestScoreSignalRelevance:
    """Tests for score_signal_relevance."""

    def test_same_industry_and_region_high_score(self) -> None:
        score = score_signal_relevance("technology", "US", "technology", "US", "hiring_trend")
        assert score >= 85

    def test_different_industry_and_region_base_score(self) -> None:
        score = score_signal_relevance("retail", "EU", "healthcare", "US", "hiring_trend")
        assert score == 30.0

    def test_related_industries_partial_boost(self) -> None:
        score = score_signal_relevance("fintech", "US", "banking", "US", "hiring_trend")
        assert score > 30.0

    def test_layoff_type_applies_weight(self) -> None:
        base = score_signal_relevance("technology", "US", "technology", "US", "hiring_trend")
        layoff = score_signal_relevance("technology", "US", "technology", "US", "layoff_alert")
        assert layoff > base


class TestPredictCompanyTrajectory:
    """Tests for predict_company_trajectory."""

    def test_empty_signals_returns_stable_low_confidence(self) -> None:
        result = predict_company_trajectory("Acme Corp", [])
        assert result.trajectory == "stable"
        assert result.confidence == 0.3
        assert "Insufficient" in result.recommendation

    def test_positive_signals_growing(self) -> None:
        signals = [
            {"signal_type": "hiring_trend", "severity": "info", "title": "Hiring 100"},
            {"signal_type": "hiring_trend", "severity": "info", "title": "Hiring 200"},
            {"signal_type": "skill_demand", "severity": "info", "title": "Skills hot"},
        ]
        result = predict_company_trajectory("GrowCo", signals)
        assert result.trajectory == "growing"
        assert result.confidence > 0.3

    def test_negative_signals_declining(self) -> None:
        signals = [
            {"signal_type": "layoff_alert", "severity": "critical", "title": "Layoffs"},
            {"signal_type": "layoff_alert", "severity": "critical", "title": "More layoffs"},
        ]
        result = predict_company_trajectory("ShrinkCo", signals)
        assert result.trajectory == "declining"

    def test_signal_summaries_capped_at_five(self) -> None:
        signals = [
            {"signal_type": "hiring_trend", "severity": "info", "title": f"Sig {i}"}
            for i in range(10)
        ]
        result = predict_company_trajectory("BigCo", signals)
        assert len(result.signals) <= 5


class TestDetectDisruptions:
    """Tests for detect_disruptions."""

    def test_empty_signals_returns_empty(self) -> None:
        result = detect_disruptions("tech", [])
        assert result == []

    def test_technology_disruption_detected(self) -> None:
        signals = [
            {"signal_type": "disruption", "description": "AI automation replacing jobs"},
        ]
        result = detect_disruptions("technology", signals)
        assert len(result) == 1
        assert result[0].disruption_type == "technology"
        assert result[0].industry == "technology"

    def test_regulation_disruption_detected(self) -> None:
        signals = [
            {"signal_type": "disruption", "description": "New regulation compliance required"},
        ]
        result = detect_disruptions("finance", signals)
        assert len(result) == 1
        assert result[0].disruption_type == "regulation"

    def test_multiple_tech_signals_high_impact(self) -> None:
        signals = [
            {"signal_type": "disruption", "description": "AI replacing tasks"},
            {"signal_type": "disruption", "description": "Automation in factories"},
            {"signal_type": "disruption", "description": "Machine learning disrupting roles"},
        ]
        result = detect_disruptions("manufacturing", signals)
        tech = [d for d in result if d.disruption_type == "technology"]
        assert len(tech) == 1
        assert tech[0].impact_level == "high"

    def test_non_disruption_signals_ignored(self) -> None:
        signals = [
            {"signal_type": "hiring_trend", "description": "Company hiring 100 engineers"},
        ]
        result = detect_disruptions("tech", signals)
        assert result == []
