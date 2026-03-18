"""Tests for posting freshness analysis and analyze_posting orchestration."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.services.trust.models import FreshnessScore
from src.services.trust.verification_service import TrustVerificationService


class TestFreshnessAnalysis:
    def test_recent_posting_high_score(self) -> None:
        posted = (datetime.now(tz=timezone.utc) - timedelta(days=2)).isoformat()
        result = TrustVerificationService.analyze_posting_freshness(posted)
        assert isinstance(result, FreshnessScore)
        assert result.score >= 90.0
        assert result.days_since_posted <= 3
        assert result.staleness_flag is False

    def test_old_posting_sets_staleness_flag(self) -> None:
        posted = (datetime.now(tz=timezone.utc) - timedelta(days=45)).isoformat()
        result = TrustVerificationService.analyze_posting_freshness(posted)
        assert result.staleness_flag is True
        assert result.days_since_posted >= 44
        assert result.score <= 20.0

    def test_very_old_posting_score_floors_at_zero(self) -> None:
        posted = (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat()
        result = TrustVerificationService.analyze_posting_freshness(posted)
        assert result.score == 0.0
        assert result.staleness_flag is True

    def test_no_posted_date_defaults_gracefully(self) -> None:
        result = TrustVerificationService.analyze_posting_freshness(None)
        assert result.score == 50.0
        assert result.days_since_posted == 0
        assert result.staleness_flag is False

    def test_invalid_date_string(self) -> None:
        result = TrustVerificationService.analyze_posting_freshness("not-a-date")
        assert result.score == 50.0
        assert result.staleness_flag is False

    def test_placeholder_fields_are_zero(self) -> None:
        posted = datetime.now(tz=timezone.utc).isoformat()
        result = TrustVerificationService.analyze_posting_freshness(posted)
        assert result.repost_frequency == 0
        assert result.similar_postings_count == 0


class TestAnalyzePosting:
    async def test_clean_jd_returns_no_flags(self) -> None:
        service = TrustVerificationService()
        result = await service.analyze_posting(
            job_title="SDE-2",
            company_name="Acme Corp",
            jd_text="Looking for experienced Python developer with 5+ years.",
        )
        assert result["overall_risk_level"] == "NONE"
        assert len(result["red_flags"]) == 0
        assert len(result["india_specific_flags"]) == 0
        assert len(result["recommended_actions"]) >= 1

    async def test_scam_jd_returns_high_risk(self) -> None:
        service = TrustVerificationService()
        result = await service.analyze_posting(
            job_title="Data Entry",
            company_name="Unknown",
            jd_text="Work from home, no experience required, earn unlimited income! Pay registration fee to start.",
        )
        assert result["overall_risk_level"] in ("HIGH", "CRITICAL")
        assert len(result["red_flags"]) >= 2

    async def test_india_locale_adds_india_flags(self) -> None:
        service = TrustVerificationService()
        result = await service.analyze_posting(
            job_title="Associate",
            company_name="Placement Agency",
            jd_text="Pay placement fee of Rs. 5000. Send resume on WhatsApp only.",
            locale="IN",
        )
        assert len(result["india_specific_flags"]) >= 1
        india_categories = {f.category for f in result["india_specific_flags"]}
        assert "PLACEMENT_FEE_ILLEGAL" in india_categories

    async def test_stale_posting_adds_action(self) -> None:
        service = TrustVerificationService()
        old_date = (datetime.now(tz=timezone.utc) - timedelta(days=45)).isoformat()
        result = await service.analyze_posting(
            job_title="Dev",
            company_name="Corp",
            jd_text="Standard engineering role.",
            posted_date=old_date,
        )
        assert result["freshness"].staleness_flag is True
        assert any("stale" in a.lower() for a in result["recommended_actions"])

    async def test_recommended_actions_for_fee_scam(self) -> None:
        service = TrustVerificationService()
        result = await service.analyze_posting(
            job_title="Dev",
            company_name="Scammy Inc",
            jd_text="You must pay a registration fee before starting.",
        )
        assert any("pay" in a.lower() for a in result["recommended_actions"])
