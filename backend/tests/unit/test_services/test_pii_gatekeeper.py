"""Tests for PIIGatekeeper — stage-based PII sharing boundaries."""

from src.services.trust.pii_gatekeeper import PIIGatekeeper


class TestPIIGatekeeperIndia:
    def setup_method(self):
        self.gatekeeper = PIIGatekeeper()

    def test_application_stage_aadhaar_inappropriate(self):
        result = self.gatekeeper.evaluate("application", "IN", ["aadhaar"])
        assert "aadhaar" in result.inappropriate_pii
        assert len(result.alerts) == 1
        assert "aadhaar" in result.alerts[0]

    def test_post_offer_stage_aadhaar_appropriate(self):
        result = self.gatekeeper.evaluate("post_offer", "IN", ["aadhaar"])
        assert "aadhaar" in result.appropriate_pii
        assert len(result.alerts) == 0

    def test_offer_stage_pan_appropriate(self):
        result = self.gatekeeper.evaluate("offer", "IN", ["pan"])
        assert "pan" in result.appropriate_pii
        assert len(result.alerts) == 0

    def test_offer_stage_bank_details_inappropriate(self):
        result = self.gatekeeper.evaluate("offer", "IN", ["bank_details"])
        assert "bank_details" in result.inappropriate_pii
        assert len(result.alerts) == 1

    def test_application_stage_basic_info_appropriate(self):
        result = self.gatekeeper.evaluate("application", "IN", ["name", "email", "phone"])
        assert "name" in result.appropriate_pii
        assert "email" in result.appropriate_pii
        assert len(result.alerts) == 0

    def test_covers_all_five_stages(self):
        stages = ["application", "phone_screen", "onsite", "offer", "post_offer"]
        for stage in stages:
            result = self.gatekeeper.evaluate(stage, "IN", [])
            assert result.hiring_stage == stage
            assert result.jurisdiction == "IN"

    def test_cumulative_pii_increases_with_stages(self):
        app_result = self.gatekeeper.evaluate("application", "IN", [])
        offer_result = self.gatekeeper.evaluate("offer", "IN", [])
        post_offer_result = self.gatekeeper.evaluate("post_offer", "IN", [])
        assert len(app_result.appropriate_pii) < len(offer_result.appropriate_pii)
        assert len(offer_result.appropriate_pii) < len(post_offer_result.appropriate_pii)


class TestPIIGatekeeperUS:
    def setup_method(self):
        self.gatekeeper = PIIGatekeeper()

    def test_application_stage_ssn_inappropriate(self):
        result = self.gatekeeper.evaluate("application", "US", ["ssn"])
        assert "ssn" in result.inappropriate_pii
        assert len(result.alerts) == 1

    def test_post_offer_stage_ssn_appropriate(self):
        result = self.gatekeeper.evaluate("post_offer", "US", ["ssn"])
        assert "ssn" in result.appropriate_pii
        assert len(result.alerts) == 0

    def test_covers_all_five_stages(self):
        stages = ["application", "phone_screen", "onsite", "offer", "post_offer"]
        for stage in stages:
            result = self.gatekeeper.evaluate(stage, "US", [])
            assert result.hiring_stage == stage
            assert result.jurisdiction == "US"

    def test_multiple_inappropriate_pii_generates_multiple_alerts(self):
        result = self.gatekeeper.evaluate("application", "US", ["ssn", "bank_details"])
        assert len(result.alerts) == 2

    def test_case_insensitive_jurisdiction(self):
        result = self.gatekeeper.evaluate("application", "us", ["ssn"])
        assert result.jurisdiction == "US"
        assert len(result.alerts) == 1
