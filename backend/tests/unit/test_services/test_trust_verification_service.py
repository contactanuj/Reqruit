"""Tests for TrustVerificationService — caching and email domain checks."""

import time
from unittest.mock import AsyncMock, patch

from src.services.trust.models import RiskCategory, RiskSignal, TrustScore
from src.services.trust.verification_service import TrustVerificationService


def _mock_agent_result(**overrides) -> dict:
    base = {
        "company_verification_score": 80.0,
        "recruiter_verification_score": 75.0,
        "posting_freshness_score": 85.0,
        "red_flag_count": 0,
        "overall_trust_score": 80.0,
        "risk_category": "LIKELY_SAFE",
        "risk_signals": [],
    }
    base.update(overrides)
    return base


class TestVerify:
    async def test_returns_trust_score(self) -> None:
        service = TrustVerificationService()
        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            result = await service.verify(company_name="Acme Corp")

        assert isinstance(result, TrustScore)
        assert result.overall_trust_score == 80.0
        assert result.risk_category == "LIKELY_SAFE"

    async def test_caching_avoids_second_agent_call(self) -> None:
        service = TrustVerificationService()
        mock_agent = AsyncMock(return_value=_mock_agent_result())

        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=mock_agent,
        ):
            result1 = await service.verify(company_name="Acme Corp")
            result2 = await service.verify(company_name="Acme Corp")

        # Agent called only once — second call hits cache
        assert mock_agent.call_count == 1
        assert result1.overall_trust_score == result2.overall_trust_score

    async def test_different_companies_are_not_cached_together(self) -> None:
        service = TrustVerificationService()
        mock_agent = AsyncMock(return_value=_mock_agent_result())

        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=mock_agent,
        ):
            await service.verify(company_name="Acme Corp")
            await service.verify(company_name="Other Corp")

        assert mock_agent.call_count == 2

    async def test_personal_email_adds_risk_signal(self) -> None:
        service = TrustVerificationService()
        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            result = await service.verify(
                company_name="Acme Corp",
                recruiter_email="recruiter@gmail.com",
            )

        signal_types = [s.signal_type for s in result.risk_signals]
        assert "PERSONAL_EMAIL_DOMAIN" in signal_types
        assert result.red_flag_count == 1

    async def test_email_domain_mismatch_adds_signal(self) -> None:
        service = TrustVerificationService()
        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            result = await service.verify(
                company_name="Acme Corp",
                recruiter_email="hr@randomdomain.com",
            )

        signal_types = [s.signal_type for s in result.risk_signals]
        assert "EMAIL_DOMAIN_MISMATCH" in signal_types

    async def test_matching_email_domain_no_signal(self) -> None:
        service = TrustVerificationService()
        with patch(
            "src.services.trust.verification_service.scam_detector_agent",
            new=AsyncMock(return_value=_mock_agent_result()),
        ):
            result = await service.verify(
                company_name="Acme Corp",
                recruiter_email="hr@acme.com",
            )

        signal_types = [s.signal_type for s in result.risk_signals]
        assert "PERSONAL_EMAIL_DOMAIN" not in signal_types
        assert "EMAIL_DOMAIN_MISMATCH" not in signal_types


class TestJobCache:
    def test_cache_and_retrieve_job_score(self) -> None:
        service = TrustVerificationService()
        score = TrustScore(overall_trust_score=90.0, risk_category=RiskCategory.VERIFIED)
        service.cache_score_for_job("job123", score)

        cached = service.get_cached_score_for_job("job123")
        assert cached is not None
        assert cached.overall_trust_score == 90.0

    def test_missing_job_returns_none(self) -> None:
        service = TrustVerificationService()
        assert service.get_cached_score_for_job("nonexistent") is None


class TestEmailDomainCheck:
    def test_no_email_returns_none(self) -> None:
        result = TrustVerificationService._check_email_domain_match(None, "Acme")
        assert result is None

    def test_personal_email_returns_signal(self) -> None:
        result = TrustVerificationService._check_email_domain_match("hr@gmail.com", "Acme")
        assert result is not None
        assert result.signal_type == "PERSONAL_EMAIL_DOMAIN"
        assert result.severity == "high"

    def test_matching_domain_returns_none(self) -> None:
        result = TrustVerificationService._check_email_domain_match("hr@acme.com", "Acme Corp")
        assert result is None

    def test_mismatched_domain_returns_signal(self) -> None:
        result = TrustVerificationService._check_email_domain_match("hr@other.com", "Acme Corp")
        assert result is not None
        assert result.signal_type == "EMAIL_DOMAIN_MISMATCH"
        assert result.severity == "medium"


class TestRiskCategoryEnum:
    def test_all_values(self) -> None:
        expected = {"VERIFIED", "LIKELY_SAFE", "UNCERTAIN", "SUSPICIOUS", "SCAM_LIKELY"}
        actual = {v.value for v in RiskCategory}
        assert actual == expected
