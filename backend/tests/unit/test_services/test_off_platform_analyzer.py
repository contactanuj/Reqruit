"""Tests for OffPlatformAlertAnalyzer — communication risk analysis."""

from src.services.trust.off_platform_analyzer import OffPlatformAlertAnalyzer


class TestOffPlatformAlertAnalyzer:
    def setup_method(self):
        self.analyzer = OffPlatformAlertAnalyzer()

    def test_upfront_payment_high_severity(self):
        flags = self.analyzer.analyze(["upfront_payment"])
        assert len(flags) == 1
        assert flags[0].behavior == "upfront_payment"
        assert flags[0].severity == "HIGH"

    def test_early_pii_request_high_severity(self):
        flags = self.analyzer.analyze(["early_pii_request"])
        assert len(flags) == 1
        assert flags[0].severity == "HIGH"

    def test_pressure_tactics_high_severity(self):
        flags = self.analyzer.analyze(["pressure_tactics"])
        assert len(flags) == 1
        assert flags[0].severity == "HIGH"

    def test_secrecy_demand_high_severity(self):
        flags = self.analyzer.analyze(["secrecy_demand"])
        assert len(flags) == 1
        assert flags[0].severity == "HIGH"

    def test_off_platform_request_medium_severity(self):
        flags = self.analyzer.analyze(["off_platform_request"])
        assert len(flags) == 1
        assert flags[0].severity == "MEDIUM"

    def test_unknown_behavior_ignored(self):
        flags = self.analyzer.analyze(["unknown_behavior"])
        assert len(flags) == 0

    def test_multiple_behaviors(self):
        flags = self.analyzer.analyze(["upfront_payment", "off_platform_request"])
        assert len(flags) == 2

    def test_empty_behaviors_returns_empty(self):
        flags = self.analyzer.analyze([])
        assert flags == []


class TestOverallRisk:
    def setup_method(self):
        self.analyzer = OffPlatformAlertAnalyzer()

    def test_high_when_any_high_flag(self):
        flags = self.analyzer.analyze(["upfront_payment", "off_platform_request"])
        assert self.analyzer.calculate_overall_risk(flags) == "HIGH"

    def test_medium_when_only_medium_flags(self):
        flags = self.analyzer.analyze(["off_platform_request"])
        assert self.analyzer.calculate_overall_risk(flags) == "MEDIUM"

    def test_low_when_no_flags(self):
        assert self.analyzer.calculate_overall_risk([]) == "LOW"


class TestRecommendedActions:
    def setup_method(self):
        self.analyzer = OffPlatformAlertAnalyzer()

    def test_generates_actions_for_flags(self):
        flags = self.analyzer.analyze(["upfront_payment"])
        actions = self.analyzer.generate_recommended_actions(flags)
        assert len(actions) == 1
        assert "pay" in actions[0].lower()

    def test_default_action_when_no_flags(self):
        actions = self.analyzer.generate_recommended_actions([])
        assert len(actions) == 1
        assert "due diligence" in actions[0].lower()

    def test_unique_actions_no_duplicates(self):
        flags = self.analyzer.analyze(["upfront_payment", "upfront_payment"])
        # Even if somehow duplicated, actions should be unique
        actions = self.analyzer.generate_recommended_actions(flags)
        assert len(actions) == len(set(actions))
