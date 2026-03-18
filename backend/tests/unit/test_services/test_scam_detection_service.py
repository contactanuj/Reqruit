"""Tests for ScamDetectionService."""

from src.services.scam_detection_service import ScamDetectionService


class TestAnalyze:
    """Tests for ScamDetectionService.analyze()."""

    def test_clean_posting_low_risk(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Senior Software Engineer",
            "description": "We are looking for a senior engineer to join our team.",
            "company_name": "Acme Corporation",
            "company_email": "hr@acmecorp.com",
            "salary_min": 100_000,
            "salary_max": 150_000,
            "contact_method": "email",
        })
        assert result["risk_level"] == "LOW"
        assert result["risk_score"] < 20
        assert len(result["flags"]) == 0

    def test_personal_email_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Developer",
            "company_name": "Some Company",
            "company_email": "hiring@gmail.com",
        })
        flags = [f for f in result["flags"] if f["rule"] == "PERSONAL_EMAIL"]
        assert len(flags) == 1
        assert flags[0]["severity"] == 20

    def test_payment_keyword_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Data Entry Operator",
            "description": "Pay a small registration fee to get started.",
            "company_name": "Quick Jobs",
        })
        flags = [f for f in result["flags"] if f["rule"] == "PAYMENT_REQUEST"]
        assert len(flags) == 1
        assert flags[0]["severity"] == 30

    def test_urgency_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Act now - Limited spots available",
            "description": "Urgent hiring for immediate start.",
            "company_name": "Fast Hire Inc",
        })
        flags = [f for f in result["flags"] if f["rule"] == "URGENCY_PRESSURE"]
        assert len(flags) == 1

    def test_vague_role_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Work from Home",
            "description": "Work from home and earn $5000 per week with simple tasks and high pay",
            "company_name": "Easy Money LLC",
        })
        flags = [f for f in result["flags"] if f["rule"] == "VAGUE_ROLE"]
        assert len(flags) == 1

    def test_extreme_salary_range_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Marketing Manager",
            "company_name": "Big Corp",
            "salary_min": 10_000,
            "salary_max": 200_000,
        })
        flags = [f for f in result["flags"] if f["rule"] == "SALARY_RANGE_EXTREME"]
        assert len(flags) == 1

    def test_normal_salary_range_not_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Engineer",
            "company_name": "Tech Corp",
            "salary_min": 80_000,
            "salary_max": 120_000,
        })
        flags = [f for f in result["flags"] if f["rule"] == "SALARY_RANGE_EXTREME"]
        assert len(flags) == 0

    def test_whatsapp_contact_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Sales Rep",
            "company_name": "Sales Co",
            "contact_method": "whatsapp",
        })
        flags = [f for f in result["flags"] if f["rule"] == "INFORMAL_CONTACT"]
        assert len(flags) == 1

    def test_telegram_contact_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Analyst",
            "company_name": "Data Inc",
            "contact_method": "telegram",
        })
        flags = [f for f in result["flags"] if f["rule"] == "INFORMAL_CONTACT"]
        assert len(flags) == 1

    def test_missing_company_name_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Mystery Job",
            "description": "Great opportunity.",
        })
        flags = [f for f in result["flags"] if f["rule"] == "MISSING_COMPANY"]
        assert len(flags) == 1

    def test_short_company_name_flagged(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Developer",
            "company_name": "AB",
        })
        flags = [f for f in result["flags"] if f["rule"] == "SUSPICIOUS_COMPANY_NAME"]
        assert len(flags) == 1

    def test_multiple_flags_accumulate_score(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Act now - Easy money",
            "description": "Pay registration fee to start. Work from home and earn unlimited",
            "company_email": "jobs@yahoo.com",
            "contact_method": "whatsapp",
        })
        assert result["risk_score"] >= 60
        assert result["risk_level"] == "CRITICAL"
        assert len(result["flags"]) >= 3

    def test_score_capped_at_100(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Act now urgent hiring limited spots",
            "description": "Pay registration fee advance payment required. Simple task high pay work from home earn",
            "company_email": "x@gmail.com",
            "contact_method": "telegram",
        })
        assert result["risk_score"] <= 100


class TestRiskLevels:
    """Tests for risk level thresholds."""

    def test_low_level(self) -> None:
        assert ScamDetectionService._score_to_level(0) == "LOW"
        assert ScamDetectionService._score_to_level(19) == "LOW"

    def test_medium_level(self) -> None:
        assert ScamDetectionService._score_to_level(20) == "MEDIUM"
        assert ScamDetectionService._score_to_level(39) == "MEDIUM"

    def test_high_level(self) -> None:
        assert ScamDetectionService._score_to_level(40) == "HIGH"
        assert ScamDetectionService._score_to_level(59) == "HIGH"

    def test_critical_level(self) -> None:
        assert ScamDetectionService._score_to_level(60) == "CRITICAL"
        assert ScamDetectionService._score_to_level(100) == "CRITICAL"


class TestRecommendations:
    """Tests for recommendation messages."""

    def test_critical_recommendation(self) -> None:
        rec = ScamDetectionService._get_recommendation("CRITICAL", [])
        assert "strongly recommend avoiding" in rec.lower()

    def test_high_recommendation(self) -> None:
        rec = ScamDetectionService._get_recommendation("HIGH", [])
        assert "research" in rec.lower()

    def test_medium_recommendation(self) -> None:
        rec = ScamDetectionService._get_recommendation("MEDIUM", [])
        assert "caution" in rec.lower()

    def test_low_recommendation(self) -> None:
        rec = ScamDetectionService._get_recommendation("LOW", [])
        assert "no significant" in rec.lower()


class TestReturnStructure:
    """Tests for the return value structure."""

    def test_has_all_keys(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({"title": "Test", "company_name": "Test Co"})
        assert "risk_score" in result
        assert "risk_level" in result
        assert "flags" in result
        assert "recommendation" in result

    def test_flags_have_required_fields(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({
            "title": "Test",
            "company_email": "x@gmail.com",
        })
        for flag in result["flags"]:
            assert "rule" in flag
            assert "severity" in flag
            assert "detail" in flag

    def test_empty_input(self) -> None:
        service = ScamDetectionService()
        result = service.analyze({})
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
