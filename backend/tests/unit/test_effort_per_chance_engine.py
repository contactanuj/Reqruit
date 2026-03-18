"""Tests for EffortPerChanceEngine — deterministic ROI prediction."""

from unittest.mock import MagicMock

from src.services.effort_per_chance_engine import (
    HIGH_ROI_THRESHOLD,
    WORTH_A_SHOT_THRESHOLD,
    CalibrationResult,
    Classification,
    ContributingFactors,
    EffortPerChanceEngine,
    calculate_probability,
    classify,
    get_historical_calibration,
    score_company_response_rate,
    score_role_competition,
    score_submission_timing,
    score_user_fit,
)


# ---------------------------------------------------------------------------
# submission_timing scoring
# ---------------------------------------------------------------------------


class TestSubmissionTiming:
    def test_0_days(self):
        assert score_submission_timing(0) == 1.0

    def test_3_days(self):
        assert score_submission_timing(3) == 1.0

    def test_4_days(self):
        assert score_submission_timing(4) == 0.7

    def test_7_days(self):
        assert score_submission_timing(7) == 0.7

    def test_8_days(self):
        assert score_submission_timing(8) == 0.4

    def test_14_days(self):
        assert score_submission_timing(14) == 0.4

    def test_15_days(self):
        assert score_submission_timing(15) == 0.2

    def test_30_days(self):
        assert score_submission_timing(30) == 0.2


# ---------------------------------------------------------------------------
# company_response_rate scoring
# ---------------------------------------------------------------------------


class TestCompanyResponseRate:
    def test_no_history_returns_default(self):
        result = score_company_response_rate(0, 0)
        assert result == 0.15  # DEFAULT_RESPONSE_RATE

    def test_with_history(self):
        result = score_company_response_rate(3, 10)
        assert result == 0.3

    def test_capped_at_1(self):
        result = score_company_response_rate(15, 10)
        assert result == 1.0


# ---------------------------------------------------------------------------
# user_fit_score scoring
# ---------------------------------------------------------------------------


class TestUserFitScore:
    def test_none_returns_default(self):
        assert score_user_fit(None) == 0.5

    def test_with_overlap(self):
        assert score_user_fit(0.8) == 0.8

    def test_clamped_above_1(self):
        assert score_user_fit(1.5) == 1.0

    def test_clamped_below_0(self):
        assert score_user_fit(-0.1) == 0.0


# ---------------------------------------------------------------------------
# role_competition_level scoring
# ---------------------------------------------------------------------------


class TestRoleCompetition:
    def test_junior_low_score(self):
        assert score_role_competition("junior") == 0.3

    def test_senior_high_score(self):
        assert score_role_competition("senior") == 0.7

    def test_unknown_returns_default(self):
        assert score_role_competition("unknown_role") == 0.5

    def test_case_insensitive(self):
        assert score_role_competition("Senior") == 0.7


# ---------------------------------------------------------------------------
# Weighted probability calculation
# ---------------------------------------------------------------------------


class TestCalculateProbability:
    def test_all_max_factors(self):
        factors = ContributingFactors(
            company_response_rate=1.0,
            role_competition_level=1.0,
            user_fit_score=1.0,
            submission_timing=1.0,
        )
        prob = calculate_probability(factors)
        assert prob == 100.0

    def test_all_zero_factors(self):
        factors = ContributingFactors(
            company_response_rate=0.0,
            role_competition_level=0.0,
            user_fit_score=0.0,
            submission_timing=0.0,
        )
        prob = calculate_probability(factors)
        assert prob == 0.0

    def test_mixed_factors(self):
        factors = ContributingFactors(
            company_response_rate=0.5,
            role_competition_level=0.5,
            user_fit_score=0.5,
            submission_timing=0.5,
        )
        prob = calculate_probability(factors)
        assert prob == 50.0


# ---------------------------------------------------------------------------
# Classification boundaries
# ---------------------------------------------------------------------------


class TestClassification:
    def test_skip_it_at_14_9(self):
        assert classify(14.9) == Classification.SKIP_IT

    def test_worth_a_shot_at_15(self):
        assert classify(15.0) == Classification.WORTH_A_SHOT

    def test_worth_a_shot_at_40(self):
        assert classify(40.0) == Classification.WORTH_A_SHOT

    def test_high_roi_at_40_1(self):
        assert classify(40.1) == Classification.HIGH_ROI


# ---------------------------------------------------------------------------
# Personalization calibration
# ---------------------------------------------------------------------------


class TestPersonalization:
    def test_under_10_apps_not_personalized(self):
        result = get_historical_calibration(5, 1)
        assert result.personalized is False
        assert result.confidence == "low"
        assert result.calibration_multiplier == 1.0

    def test_10_to_49_apps_partial(self):
        result = get_historical_calibration(25, 5)
        assert result.personalized is True
        assert result.confidence == "medium"

    def test_50_plus_apps_full(self):
        result = get_historical_calibration(60, 12)
        assert result.personalized is True
        assert result.confidence == "high"

    def test_0_apps_not_personalized(self):
        result = get_historical_calibration(0, 0)
        assert result.personalized is False
        assert result.confidence == "low"

    def test_calibration_multiplier_clamped(self):
        # Very high personal rate → multiplier capped at 3.0
        result = get_historical_calibration(50, 45)
        assert result.calibration_multiplier <= 3.0


# ---------------------------------------------------------------------------
# Engine predict
# ---------------------------------------------------------------------------


class TestEnginePredict:
    def test_predict_returns_all_fields(self):
        repo = MagicMock()
        engine = EffortPerChanceEngine(user_activity_repo=repo)

        result = engine.predict(
            company_apps=0,
            company_responses=0,
            seniority_level="mid",
            skill_overlap_pct=None,
            days_since_posted=5,
            total_user_apps=0,
            total_user_responses=0,
        )

        assert 0 <= result.probability_of_response <= 100
        assert result.classification in ("HIGH_ROI", "WORTH_A_SHOT", "SKIP_IT")
        assert result.contributing_factors is not None
        assert result.confidence in ("high", "medium", "low")

    def test_predict_with_personalization(self):
        repo = MagicMock()
        engine = EffortPerChanceEngine(user_activity_repo=repo)

        result = engine.predict(
            company_apps=10,
            company_responses=5,
            seniority_level="senior",
            skill_overlap_pct=0.8,
            days_since_posted=2,
            total_user_apps=60,
            total_user_responses=15,
        )

        assert result.personalized is True
        assert result.confidence == "high"
