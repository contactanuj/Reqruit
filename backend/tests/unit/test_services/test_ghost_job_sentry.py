"""Tests for GhostJobSentry — ghost job liveness scoring."""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from src.services.trust.ghost_job_sentry import GhostJobSentry


def _mock_repo(distinct_count=0, has_badge=False):
    repo = AsyncMock()
    repo.get_distinct_reporter_count = AsyncMock(return_value=distinct_count)
    repo.has_warning_badge = AsyncMock(return_value=has_badge)
    return repo


def _date_ago(days: int) -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()


class TestDaysSincePostedDecay:
    def test_zero_days_returns_near_100(self):
        signal = GhostJobSentry._days_since_posted_decay(_date_ago(0))
        assert signal.signal_value >= 99.0

    def test_60_days_returns_low_score(self):
        signal = GhostJobSentry._days_since_posted_decay(_date_ago(60))
        expected = round(100.0 * math.exp(-0.03 * 60), 1)
        assert signal.signal_value == expected
        assert signal.signal_value < 20

    def test_no_date_returns_neutral(self):
        signal = GhostJobSentry._days_since_posted_decay(None)
        assert signal.signal_value == 50.0

    def test_invalid_date_returns_neutral(self):
        signal = GhostJobSentry._days_since_posted_decay("not-a-date")
        assert signal.signal_value == 50.0


class TestGhostJobSentryCheck:
    async def test_recent_posting_high_liveness(self):
        repo = _mock_repo(distinct_count=0, has_badge=False)
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Good Corp",
            job_title="Engineer",
            posted_date=_date_ago(5),
        )

        assert result["liveness_score"] > 60
        assert result["verdict"] in ("likely_active", "uncertain")

    async def test_old_posting_low_liveness(self):
        repo = _mock_repo(distinct_count=5, has_badge=True)
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Scam Corp",
            job_title="Associate",
            posted_date=_date_ago(90),
        )

        assert result["liveness_score"] < 30
        assert result["verdict"] == "likely_ghost"

    async def test_likely_ghost_includes_warning(self):
        repo = _mock_repo(distinct_count=5, has_badge=True)
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Bad Corp",
            job_title="Test",
            posted_date=_date_ago(120),
        )

        assert result["warning"] is not None
        assert "ghost" in result["warning"].lower()

    async def test_likely_active_no_warning(self):
        repo = _mock_repo(distinct_count=0, has_badge=False)
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Good Corp",
            job_title="Engineer",
            posted_date=_date_ago(2),
        )

        assert result["warning"] is None

    async def test_uncertain_recommendation(self):
        repo = _mock_repo(distinct_count=1, has_badge=False)
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Corp",
            job_title="Dev",
            posted_date=_date_ago(30),
        )

        if result["verdict"] == "uncertain":
            assert "caution" in result["recommendation"].lower()

    async def test_always_5_signals(self):
        repo = _mock_repo()
        sentry = GhostJobSentry(repo)

        result = await sentry.check(
            company_name="Corp",
            job_title="Dev",
        )

        assert len(result["signals"]) == 5

    async def test_score_clamped_0_to_100(self):
        repo = _mock_repo()
        sentry = GhostJobSentry(repo)

        result = await sentry.check(company_name="Corp", job_title="Dev")

        assert 0 <= result["liveness_score"] <= 100


class TestWeightedScore:
    def test_weighted_average(self):
        from src.services.trust.models import LivenessSignal
        signals = [
            LivenessSignal(signal_name="a", signal_value=100.0, weight=0.5, description=""),
            LivenessSignal(signal_name="b", signal_value=0.0, weight=0.5, description=""),
        ]
        score = GhostJobSentry._compute_weighted_score(signals)
        assert score == 50.0

    def test_empty_signals_returns_neutral(self):
        score = GhostJobSentry._compute_weighted_score([])
        assert score == 50.0
