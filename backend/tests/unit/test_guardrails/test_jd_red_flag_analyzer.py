"""Tests for JDRedFlagAnalyzer — rule-based JD red flag detection."""

from src.guardrails.jd_red_flag_analyzer import JDRedFlagAnalyzer


class TestUniversalFlags:
    def test_detects_upfront_fee_as_high_risk(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("You must pay a registration fee of $500 before onboarding.")
        assert len(flags) >= 1
        fee_flags = [f for f in flags if f.category == "UPFRONT_FEE"]
        assert len(fee_flags) == 1
        assert fee_flags[0].severity == "HIGH_RISK"

    def test_detects_processing_fee(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("A processing fee is required to proceed with your application.")
        categories = {f.category for f in flags}
        assert "UPFRONT_FEE" in categories

    def test_detects_telegram_only_as_medium_risk(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("Contact us on Telegram only for this position.")
        tg_flags = [f for f in flags if f.category == "TELEGRAM_ONLY"]
        assert len(tg_flags) == 1
        assert tg_flags[0].severity == "MEDIUM_RISK"

    def test_detects_vague_wfh_as_high_risk(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("Work from home opportunity, no experience required, earn unlimited income!")
        wfh_flags = [f for f in flags if f.category == "VAGUE_WFH"]
        assert len(wfh_flags) == 1
        assert wfh_flags[0].severity == "HIGH_RISK"

    def test_detects_simple_task_high_pay(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("Simple task with high pay, anyone can do it.")
        categories = {f.category for f in flags}
        assert "VAGUE_WFH" in categories

    def test_detects_urgency_pressure_as_medium_risk(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("Immediate start required, act now before limited spots fill up!")
        urgency_flags = [f for f in flags if f.category == "URGENCY_PRESSURE"]
        assert len(urgency_flags) == 1
        assert urgency_flags[0].severity == "MEDIUM_RISK"

    def test_clean_jd_returns_empty(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        jd = (
            "We are looking for a Senior Software Engineer with 5+ years of experience "
            "in Python and distributed systems. Competitive salary and benefits. "
            "Please apply through our careers page at acme.com/careers."
        )
        flags = analyzer.analyze(jd)
        assert len(flags) == 0

    def test_clean_jd_no_india_flags_for_us(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze("Great opportunity at Acme Corp.", locale="US")
        india_categories = {"PLACEMENT_FEE_ILLEGAL", "WHATSAPP_ONLY"}
        india_flags = [f for f in flags if f.category in india_categories]
        assert len(india_flags) == 0


class TestIndiaSpecificFlags:
    def test_placement_fee_as_high_risk(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze(
            "You need to pay a placement fee of Rs. 5000 before joining.",
            locale="IN",
        )
        pf_flags = [f for f in flags if f.category == "PLACEMENT_FEE_ILLEGAL"]
        assert len(pf_flags) == 1
        assert pf_flags[0].severity == "HIGH_RISK"
        assert "illegal" in pf_flags[0].explanation.lower()

    def test_consultancy_fee_flagged(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze(
            "Consultancy charge applicable for candidates selected through our agency.",
            locale="IN",
        )
        categories = {f.category for f in flags}
        assert "PLACEMENT_FEE_ILLEGAL" in categories

    def test_whatsapp_only_flagged(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze(
            "Send your resume on WhatsApp only to our HR team.",
            locale="IN",
        )
        wa_flags = [f for f in flags if f.category == "WHATSAPP_ONLY"]
        assert len(wa_flags) == 1
        assert wa_flags[0].severity == "MEDIUM_RISK"

    def test_india_flags_not_triggered_for_us_locale(self) -> None:
        analyzer = JDRedFlagAnalyzer()
        flags = analyzer.analyze(
            "You need to pay a placement fee of Rs. 5000.",
            locale="US",
        )
        india_flags = [f for f in flags if f.category == "PLACEMENT_FEE_ILLEGAL"]
        assert len(india_flags) == 0
