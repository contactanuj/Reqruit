"""Tests for early_warning_service — career risk signal detection."""

from src.db.documents.career_vitals import CareerVitals, DriftIndicator, HealthMetric
from src.services.early_warning_service import (
    evaluate_drift_indicators,
    evaluate_vitals,
    generate_early_warnings,
)

_USER_ID = "a" * 24  # valid 24-hex-char PydanticObjectId


def _make_vitals(
    metrics: list[HealthMetric] | None = None,
    drift_indicators: list[DriftIndicator] | None = None,
) -> CareerVitals:
    return CareerVitals(
        user_id=_USER_ID,
        metrics=metrics or [],
        drift_indicators=drift_indicators or [],
    )


class TestEvaluateVitals:
    """Tests for evaluate_vitals threshold logic."""

    def test_empty_metrics_returns_no_signals(self) -> None:
        vitals = _make_vitals(metrics=[])
        signals = evaluate_vitals(vitals)
        assert signals == []

    def test_high_scores_produce_no_signals(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=90, trend="stable"),
            HealthMetric(name="market_demand", score=85, trend="improving"),
        ])
        signals = evaluate_vitals(vitals)
        assert signals == []

    def test_critical_threshold_skill_relevance(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=35, trend="stable"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 1
        assert signals[0].severity == "critical"
        assert signals[0].signal_type == "skill_decay"

    def test_warning_threshold_skill_relevance(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=55, trend="stable"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 1
        assert signals[0].severity == "warning"

    def test_declining_trend_elevates_warning_to_high(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=55, trend="declining"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 1
        assert signals[0].severity == "high"

    def test_declining_trend_near_warning_generates_low(self) -> None:
        """Score above warning but within +15 range with declining trend -> low."""
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=70, trend="declining"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 1
        assert signals[0].severity == "low"

    def test_unknown_metric_name_ignored(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="unknown_metric", score=10, trend="declining"),
        ])
        signals = evaluate_vitals(vitals)
        assert signals == []

    def test_boundary_score_at_critical_exact(self) -> None:
        """Score exactly at critical threshold (40) is critical."""
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=40, trend="stable"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 1
        assert signals[0].severity == "critical"

    def test_multiple_metrics_produce_multiple_signals(self) -> None:
        vitals = _make_vitals(metrics=[
            HealthMetric(name="skill_relevance", score=30, trend="declining"),
            HealthMetric(name="market_demand", score=25, trend="declining"),
            HealthMetric(name="compensation_alignment", score=30, trend="stable"),
        ])
        signals = evaluate_vitals(vitals)
        assert len(signals) == 3
        types = {s.signal_type for s in signals}
        assert "skill_decay" in types
        assert "market_contraction" in types
        assert "compensation_drift" in types


class TestEvaluateDriftIndicators:
    """Tests for evaluate_drift_indicators."""

    def test_empty_indicators_returns_empty(self) -> None:
        signals = evaluate_drift_indicators([])
        assert signals == []

    def test_single_indicator_produces_signal(self) -> None:
        indicator = DriftIndicator(
            category="skill_gap",
            severity="high",
            description="Skills diverging from market needs.",
            recommended_action="Take a course.",
        )
        signals = evaluate_drift_indicators([indicator])
        assert len(signals) == 1
        assert signals[0].signal_type == "skill_gap"
        assert signals[0].severity == "high"
        assert signals[0].recommended_action == "Take a course."

    def test_indicator_without_action_uses_default(self) -> None:
        indicator = DriftIndicator(
            category="stagnation",
            severity="medium",
            description="Career growth stalled.",
            recommended_action="",
        )
        signals = evaluate_drift_indicators([indicator])
        assert len(signals) == 1
        assert "stretch assignments" in signals[0].recommended_action.lower()


class TestGenerateEarlyWarnings:
    """Tests for generate_early_warnings (combines vitals + drift)."""

    def test_combines_vitals_and_drift(self) -> None:
        vitals = _make_vitals(
            metrics=[
                HealthMetric(name="skill_relevance", score=30, trend="stable"),
            ],
            drift_indicators=[
                DriftIndicator(
                    category="market_shift",
                    severity="low",
                    description="Market shifting.",
                ),
            ],
        )
        signals = generate_early_warnings(vitals)
        assert len(signals) == 2

    def test_sorted_by_severity(self) -> None:
        vitals = _make_vitals(
            metrics=[
                HealthMetric(name="skill_relevance", score=55, trend="stable"),  # warning
                HealthMetric(name="market_demand", score=20, trend="stable"),  # critical
            ],
        )
        signals = generate_early_warnings(vitals)
        assert len(signals) == 2
        assert signals[0].severity == "critical"
        assert signals[1].severity == "warning"

    def test_empty_vitals_returns_empty(self) -> None:
        vitals = _make_vitals()
        signals = generate_early_warnings(vitals)
        assert signals == []
