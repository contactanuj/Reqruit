"""
GhostJobSentry — rule-based ghost job liveness scoring.

Evaluates 5+ signals to determine whether a job posting is likely active,
uncertain, or a ghost listing. No LLM calls — pure computation.
"""

import math

from src.repositories.scam_report_repository import ScamReportRepository
from src.services.trust.models import LivenessSignal


_VERDICT_GHOST_THRESHOLD = 30
_VERDICT_ACTIVE_THRESHOLD = 70


class GhostJobSentry:
    """Evaluates job posting liveness using weighted signal analysis."""

    def __init__(self, scam_report_repo: ScamReportRepository) -> None:
        self._repo = scam_report_repo

    async def check(
        self,
        job_url: str | None = None,
        company_name: str | None = None,
        job_title: str | None = None,
        posted_date: str | None = None,
    ) -> dict:
        """Run all signals and return liveness verdict."""
        signals: list[LivenessSignal] = []

        signals.append(self._days_since_posted_decay(posted_date))
        signals.append(await self._repost_frequency(company_name, job_title))
        signals.append(self._company_career_page_match(company_name, job_title))
        signals.append(await self._recruiter_activity_recency(company_name))
        signals.append(self._similar_postings_count(job_title))

        score = self._compute_weighted_score(signals)
        verdict = self._determine_verdict(score)
        warning = self._generate_warning(verdict, signals)
        recommendation = self._generate_recommendation(verdict)

        return {
            "liveness_score": round(score, 1),
            "verdict": verdict,
            "signals": signals,
            "warning": warning,
            "recommendation": recommendation,
        }

    @staticmethod
    def _days_since_posted_decay(posted_date: str | None) -> LivenessSignal:
        """Exponential decay: score = 100 * exp(-0.03 * days)."""
        if not posted_date:
            return LivenessSignal(
                signal_name="days_since_posted",
                signal_value=50.0,
                weight=0.25,
                description="No posting date provided — neutral score",
            )

        from datetime import datetime, timezone
        try:
            posted_dt = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            days = max(0, (now - posted_dt).days)
        except (ValueError, TypeError):
            return LivenessSignal(
                signal_name="days_since_posted",
                signal_value=50.0,
                weight=0.25,
                description="Invalid posting date — neutral score",
            )

        value = 100.0 * math.exp(-0.03 * days)
        return LivenessSignal(
            signal_name="days_since_posted",
            signal_value=round(value, 1),
            weight=0.25,
            description=f"Posted {days} days ago — {'fresh' if days < 14 else 'aging' if days < 45 else 'stale'}",
        )

    async def _repost_frequency(
        self, company_name: str | None, job_title: str | None
    ) -> LivenessSignal:
        """Check ScamReport for repeated postings — high repost = lower liveness."""
        if not company_name:
            return LivenessSignal(
                signal_name="repost_frequency",
                signal_value=50.0,
                weight=0.20,
                description="No company name — neutral repost score",
            )

        entity_id = company_name.lower().strip()
        count = await self._repo.get_distinct_reporter_count(entity_id)
        # More reports = lower liveness (inverse signal)
        value = max(0.0, 100.0 - (count * 20.0))
        return LivenessSignal(
            signal_name="repost_frequency",
            signal_value=round(value, 1),
            weight=0.20,
            description=f"{count} community reports for this entity",
        )

    @staticmethod
    def _company_career_page_match(
        company_name: str | None, job_title: str | None
    ) -> LivenessSignal:
        """Placeholder — future: verify posting exists on company careers page."""
        return LivenessSignal(
            signal_name="career_page_match",
            signal_value=50.0,
            weight=0.20,
            description="Career page verification not yet available — neutral score",
        )

    async def _recruiter_activity_recency(
        self, company_name: str | None
    ) -> LivenessSignal:
        """Check if recent scam reports exist for company (inverse signal)."""
        if not company_name:
            return LivenessSignal(
                signal_name="recruiter_activity",
                signal_value=50.0,
                weight=0.15,
                description="No company name — neutral recruiter activity score",
            )

        entity_id = company_name.lower().strip()
        has_badge = await self._repo.has_warning_badge(entity_id)
        value = 10.0 if has_badge else 70.0
        desc = "Warning badge active — reduced liveness" if has_badge else "No warning badge — positive signal"
        return LivenessSignal(
            signal_name="recruiter_activity",
            signal_value=value,
            weight=0.15,
            description=desc,
        )

    @staticmethod
    def _similar_postings_count(job_title: str | None) -> LivenessSignal:
        """Placeholder for cross-platform deduplication."""
        return LivenessSignal(
            signal_name="similar_postings",
            signal_value=50.0,
            weight=0.20,
            description="Cross-platform dedup not yet available — neutral score",
        )

    @staticmethod
    def _compute_weighted_score(signals: list[LivenessSignal]) -> float:
        """Weighted average of all signal values, clamped 0-100."""
        total_weight = sum(s.weight for s in signals)
        if total_weight == 0:
            return 50.0
        weighted_sum = sum(s.signal_value * s.weight for s in signals)
        return max(0.0, min(100.0, weighted_sum / total_weight))

    @staticmethod
    def _determine_verdict(score: float) -> str:
        if score < _VERDICT_GHOST_THRESHOLD:
            return "likely_ghost"
        if score > _VERDICT_ACTIVE_THRESHOLD:
            return "likely_active"
        return "uncertain"

    @staticmethod
    def _generate_warning(verdict: str, signals: list[LivenessSignal]) -> str | None:
        if verdict != "likely_ghost":
            return None
        low_signals = [s for s in signals if s.signal_value < 30]
        names = ", ".join(s.signal_name for s in low_signals) if low_signals else "multiple factors"
        return f"Likely ghost job — low scores on: {names}"

    @staticmethod
    def _generate_recommendation(verdict: str) -> str:
        if verdict == "likely_ghost":
            return "Consider skipping or deprioritizing this posting"
        if verdict == "likely_active":
            return "This posting appears active — proceed with application"
        return "Exercise caution — verify the posting through the company's official career page"
