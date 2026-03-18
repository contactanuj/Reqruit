"""Tests for DamageControlAssistant — post-scam recovery plan generation."""

from src.services.trust.damage_control_assistant import DamageControlAssistant


class TestCommonImmediateActions:
    def setup_method(self):
        self.assistant = DamageControlAssistant()

    def test_includes_password_change(self):
        plan = self.assistant.generate_plan("fake_offer", [], "US")
        actions = [s.action.lower() for s in plan.immediate_actions]
        assert any("password" in a for a in actions)

    def test_includes_2fa(self):
        plan = self.assistant.generate_plan("fake_offer", [], "US")
        actions = [s.action.lower() for s in plan.immediate_actions]
        assert any("two-factor" in a or "2fa" in a for a in actions)

    def test_financial_fraud_includes_account_freeze(self):
        plan = self.assistant.generate_plan("financial_fraud", [], "IN")
        actions = [s.action.lower() for s in plan.immediate_actions]
        assert any("freeze" in a for a in actions)

    def test_all_steps_have_required_fields(self):
        plan = self.assistant.generate_plan("identity_theft", ["email"], "US")
        all_steps = (
            plan.immediate_actions
            + plan.complaint_filing
            + plan.monitoring_steps
            + plan.platform_flagging
        )
        for step in all_steps:
            assert step.step_number > 0
            assert step.action
            assert step.details
            assert step.urgency in ("immediate", "within_24h", "within_week", "ongoing")


class TestIndiaJurisdiction:
    def setup_method(self):
        self.assistant = DamageControlAssistant()

    def test_includes_cybercrime_gov_in(self):
        plan = self.assistant.generate_plan("identity_theft", [], "IN")
        urls = [s.url for s in plan.complaint_filing if s.url]
        assert any("cybercrime.gov.in" in u for u in urls)

    def test_financial_fraud_includes_rbi(self):
        plan = self.assistant.generate_plan("financial_fraud", [], "IN")
        urls = [s.url for s in plan.complaint_filing if s.url]
        assert any("rbi" in u for u in urls)

    def test_aadhaar_shared_includes_lock(self):
        plan = self.assistant.generate_plan("identity_theft", ["aadhaar"], "IN")
        actions = [s.action.lower() for s in plan.complaint_filing]
        assert any("aadhaar" in a for a in actions)

    def test_pan_shared_includes_income_tax(self):
        plan = self.assistant.generate_plan("identity_theft", ["pan"], "IN")
        actions = [s.action.lower() for s in plan.complaint_filing]
        assert any("pan" in a for a in actions)

    def test_platform_flagging_includes_naukri(self):
        plan = self.assistant.generate_plan("fake_offer", [], "IN")
        actions = [s.action.lower() for s in plan.platform_flagging]
        assert any("naukri" in a for a in actions)


class TestUSJurisdiction:
    def setup_method(self):
        self.assistant = DamageControlAssistant()

    def test_includes_ftc(self):
        plan = self.assistant.generate_plan("identity_theft", [], "US")
        urls = [s.url for s in plan.complaint_filing if s.url]
        assert any("identitytheft.gov" in u for u in urls)

    def test_includes_ic3(self):
        plan = self.assistant.generate_plan("identity_theft", [], "US")
        urls = [s.url for s in plan.complaint_filing if s.url]
        assert any("ic3.gov" in u for u in urls)

    def test_includes_all_3_credit_bureaus(self):
        plan = self.assistant.generate_plan("identity_theft", [], "US")
        actions = " ".join(s.action.lower() for s in plan.complaint_filing)
        assert "equifax" in actions
        assert "experian" in actions
        assert "transunion" in actions

    def test_ssn_shared_includes_ssa_and_irs(self):
        plan = self.assistant.generate_plan("identity_theft", ["ssn"], "US")
        actions = [s.action.lower() for s in plan.complaint_filing]
        assert any("social security" in a for a in actions)
        assert any("irs" in a for a in actions)

    def test_platform_flagging_includes_indeed(self):
        plan = self.assistant.generate_plan("fake_offer", [], "US")
        actions = [s.action.lower() for s in plan.platform_flagging]
        assert any("indeed" in a for a in actions)


class TestRecoveryPlanStructure:
    def setup_method(self):
        self.assistant = DamageControlAssistant()

    def test_plan_has_all_sections(self):
        plan = self.assistant.generate_plan("data_breach", ["email"], "US")
        assert len(plan.immediate_actions) >= 1
        assert len(plan.complaint_filing) >= 1
        assert len(plan.monitoring_steps) >= 1
        assert len(plan.platform_flagging) >= 1
        assert len(plan.additional_recommendations) >= 1

    def test_monitoring_includes_credit_monitoring(self):
        plan = self.assistant.generate_plan("financial_fraud", [], "US")
        actions = [s.action.lower() for s in plan.monitoring_steps]
        assert any("credit" in a or "monitor" in a for a in actions)
