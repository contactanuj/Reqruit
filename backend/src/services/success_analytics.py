"""
Success analytics service — computes rate breakdowns from outcome tracker data.

Pure Python computation service (no LLM). Aggregates ApplicationSuccessTracker
documents to produce response rates, strategy breakdowns, and timing analysis.
Also provides legacy Application-based analytics for backward-compatible routes.
"""

from collections import Counter

import structlog
from beanie import PydanticObjectId
from pydantic import BaseModel

from src.db.documents.enums import OutcomeStatus
from src.repositories.success_tracker_repository import ApplicationSuccessTrackerRepository

logger = structlog.get_logger()

# Statuses that count as having reached each milestone (cumulative)
_VIEWED_STATUSES = {
    OutcomeStatus.VIEWED,
    OutcomeStatus.RESPONDED,
    OutcomeStatus.INTERVIEW_SCHEDULED,
    OutcomeStatus.OFFER_RECEIVED,
}
_RESPONDED_STATUSES = {
    OutcomeStatus.RESPONDED,
    OutcomeStatus.INTERVIEW_SCHEDULED,
    OutcomeStatus.OFFER_RECEIVED,
}
_INTERVIEW_STATUSES = {
    OutcomeStatus.INTERVIEW_SCHEDULED,
    OutcomeStatus.OFFER_RECEIVED,
}

MIN_DATA_THRESHOLD = 5
_MAX_TRACKERS_FETCH = 10000


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RateBreakdown(BaseModel):
    total: int
    count: int
    rate: float


class FieldBreakdown(BaseModel):
    value: str
    count: int
    rate: float


class TimeBreakdown(BaseModel):
    bucket: str | int
    count: int


class AnalyticsSummaryResponse(BaseModel):
    total_applications: int
    data_sufficiency: str
    response_rate: RateBreakdown
    view_rate: RateBreakdown
    interview_rate: RateBreakdown
    breakdown_by_submission_method: list[FieldBreakdown]
    breakdown_by_resume_strategy: list[FieldBreakdown]
    breakdown_by_day_of_week: list[TimeBreakdown]
    breakdown_by_time_of_day: list[TimeBreakdown]
    message: str | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SuccessAnalyticsService:
    """Computes analytics summary from ApplicationSuccessTracker documents."""

    def __init__(self, tracker_repo: ApplicationSuccessTrackerRepository) -> None:
        self._tracker_repo = tracker_repo

    async def get_summary(self, user_id: PydanticObjectId) -> AnalyticsSummaryResponse:
        """Compute full analytics summary for a user."""
        trackers = await self._tracker_repo.get_for_user(
            user_id=user_id, limit=_MAX_TRACKERS_FETCH,
        )

        total = len(trackers)
        sufficiency = self._assess_data_sufficiency(total)
        rates = self._compute_rates(trackers)

        by_method = self._breakdown_by_field(trackers, "submission_method")
        by_strategy = self._breakdown_by_field(trackers, "resume_strategy")
        by_dow = self._breakdown_by_day_of_week(trackers)
        by_hour = self._breakdown_by_time_of_day(trackers)

        message = None
        if sufficiency == "low":
            message = (
                "Fewer than 5 tracked applications. "
                "Analytics may not reflect reliable patterns."
            )

        logger.info(
            "analytics_computed",
            user_id=str(user_id),
            total_applications=total,
            data_sufficiency=sufficiency,
        )

        return AnalyticsSummaryResponse(
            total_applications=total,
            data_sufficiency=sufficiency,
            response_rate=rates["response_rate"],
            view_rate=rates["view_rate"],
            interview_rate=rates["interview_rate"],
            breakdown_by_submission_method=by_method,
            breakdown_by_resume_strategy=by_strategy,
            breakdown_by_day_of_week=by_dow,
            breakdown_by_time_of_day=by_hour,
            message=message,
        )

    def _compute_rates(self, trackers: list) -> dict[str, RateBreakdown]:
        """Calculate cumulative response, view, and interview rates."""
        total = len(trackers)
        if total == 0:
            zero = RateBreakdown(total=0, count=0, rate=0.0)
            return {"response_rate": zero, "view_rate": zero, "interview_rate": zero}

        viewed = sum(1 for t in trackers if t.outcome_status in _VIEWED_STATUSES)
        responded = sum(1 for t in trackers if t.outcome_status in _RESPONDED_STATUSES)
        interviewed = sum(1 for t in trackers if t.outcome_status in _INTERVIEW_STATUSES)

        return {
            "view_rate": RateBreakdown(total=total, count=viewed, rate=round(viewed / total, 4)),
            "response_rate": RateBreakdown(total=total, count=responded, rate=round(responded / total, 4)),
            "interview_rate": RateBreakdown(total=total, count=interviewed, rate=round(interviewed / total, 4)),
        }

    def _breakdown_by_field(self, trackers: list, field: str) -> list[FieldBreakdown]:
        """Group trackers by a string field, return counts and rates."""
        total = len(trackers)
        if total == 0:
            return []

        counts: Counter = Counter()
        for t in trackers:
            value = getattr(t, field, "") or "unknown"
            counts[value] += 1

        return [
            FieldBreakdown(value=val, count=cnt, rate=round(cnt / total, 4))
            for val, cnt in counts.most_common()
        ]

    def _breakdown_by_day_of_week(self, trackers: list) -> list[TimeBreakdown]:
        """Group by submitted_at day of week (Monday=0)."""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        counts: Counter = Counter()
        for t in trackers:
            if t.submitted_at is not None:
                counts[t.submitted_at.weekday()] += 1

        return [
            TimeBreakdown(bucket=day_names[day], count=cnt)
            for day, cnt in sorted(counts.items())
        ]

    def _breakdown_by_time_of_day(self, trackers: list) -> list[TimeBreakdown]:
        """Group by submitted_at hour (0-23)."""
        counts: Counter = Counter()
        for t in trackers:
            if t.submitted_at is not None:
                counts[t.submitted_at.hour] += 1

        return [
            TimeBreakdown(bucket=hour, count=cnt)
            for hour, cnt in sorted(counts.items())
        ]

    def _assess_data_sufficiency(self, count: int) -> str:
        """Return 'sufficient' if count >= threshold, else 'low'."""
        return "sufficient" if count >= MIN_DATA_THRESHOLD else "low"

    # ------------------------------------------------------------------
    # A/B Version Comparison (Story 8.4)
    # ------------------------------------------------------------------

    async def get_ab_comparison(
        self, user_id: PydanticObjectId, compare_by: str = "resume_strategy"
    ) -> dict:
        """Compare performance across strategy variants."""
        trackers = await self._tracker_repo.get_for_user(user_id=user_id, limit=_MAX_TRACKERS_FETCH)

        if not trackers:
            return {
                "comparison_possible": False,
                "compare_by": compare_by,
                "versions": [],
                "message": "No tracked applications found. Start tracking outcomes to enable comparison.",
            }

        groups: dict[str, list] = {}
        for t in trackers:
            strategy = getattr(t, compare_by, "") or "unspecified"
            groups.setdefault(strategy, []).append(t)

        if len(groups) < 2:
            return {
                "comparison_possible": False,
                "compare_by": compare_by,
                "versions": [],
                "message": "Only one strategy found. Try varying your approach to enable A/B comparison.",
            }

        versions = []
        for strategy_name, items in groups.items():
            total = len(items)
            viewed = sum(1 for t in items if t.outcome_status in _VIEWED_STATUSES)
            responded = sum(1 for t in items if t.outcome_status in _RESPONDED_STATUSES)
            interviewed = sum(1 for t in items if t.outcome_status in _INTERVIEW_STATUSES)

            versions.append({
                "strategy_name": strategy_name,
                "sample_size": total,
                "response_rate": round(responded / total, 4) if total else 0.0,
                "view_rate": round(viewed / total, 4) if total else 0.0,
                "interview_rate": round(interviewed / total, 4) if total else 0.0,
                "significance": "sufficient" if total >= 10 else "inconclusive",
            })

        versions.sort(key=lambda v: v["response_rate"], reverse=True)

        return {
            "comparison_possible": True,
            "compare_by": compare_by,
            "versions": versions,
            "message": "",
        }

    # ------------------------------------------------------------------
    # Timing analysis (Story 8.3)
    # ------------------------------------------------------------------

    async def get_timing_analysis(self, user_id: PydanticObjectId) -> dict:
        """Identify optimal submission windows by day-of-week and time bucket."""
        trackers = await self._tracker_repo.get_for_user(user_id=user_id, limit=_MAX_TRACKERS_FETCH)
        with_time = [t for t in trackers if t.submitted_at is not None]

        if not with_time:
            return {"windows": [], "confidence": confidence_level(0)}

        buckets: dict[tuple[str, str], dict] = {}
        for t in with_time:
            day = t.submitted_at.strftime("%A")
            hour = t.submitted_at.hour
            time_bucket = (
                "morning" if 6 <= hour < 12
                else "afternoon" if 12 <= hour < 17
                else "evening" if 17 <= hour < 21
                else "night"
            )
            key = (day, time_bucket)
            if key not in buckets:
                buckets[key] = {"total": 0, "responded": 0}
            buckets[key]["total"] += 1
            if t.outcome_status in _RESPONDED_STATUSES:
                buckets[key]["responded"] += 1

        windows = sorted(
            [
                {
                    "day_of_week": k[0],
                    "time_bucket": k[1],
                    "sample_size": v["total"],
                    "response_rate": round(v["responded"] / v["total"], 4) if v["total"] else 0.0,
                    "confidence": confidence_level(v["total"]),
                }
                for k, v in buckets.items()
            ],
            key=lambda x: x["response_rate"],
            reverse=True,
        )
        return {"windows": windows, "confidence": confidence_level(len(with_time))}

    # ------------------------------------------------------------------
    # Strategy comparison (Story 8.3)
    # ------------------------------------------------------------------

    async def get_strategy_comparison(self, user_id: PydanticObjectId) -> dict:
        """Compare response rates across resume and cover letter strategies."""
        trackers = await self._tracker_repo.get_for_user(user_id=user_id, limit=_MAX_TRACKERS_FETCH)
        if not trackers:
            return {
                "resume_strategies": [],
                "cover_letter_strategies": [],
                "confidence": confidence_level(0),
            }

        resume_stats = _group_by_strategy(trackers, "resume_strategy")
        cl_stats = _group_by_strategy(trackers, "cover_letter_strategy")

        return {
            "resume_strategies": resume_stats,
            "cover_letter_strategies": cl_stats,
            "confidence": confidence_level(len(trackers)),
        }

    # ------------------------------------------------------------------
    # Legacy Application-based methods (backward compat for existing routes)
    # ------------------------------------------------------------------

    async def get_response_rate(self, user_id: PydanticObjectId) -> dict:
        """Calculate response rate from tracker data."""
        trackers = await self._tracker_repo.get_for_user(user_id=user_id, limit=_MAX_TRACKERS_FETCH)
        if not trackers:
            return {"total": 0, "response_rate": 0.0, "by_method": {}}

        total = len(trackers)
        responded = sum(1 for t in trackers if t.outcome_status in _RESPONDED_STATUSES)

        by_method: dict[str, dict] = {}
        for t in trackers:
            method = t.submission_method or "unknown"
            if method not in by_method:
                by_method[method] = {"total": 0, "responded": 0}
            by_method[method]["total"] += 1
            if t.outcome_status in _RESPONDED_STATUSES:
                by_method[method]["responded"] += 1

        for data in by_method.values():
            data["rate"] = round(data["responded"] / data["total"], 4) if data["total"] else 0.0

        return {
            "total": total,
            "response_rate": round(responded / total, 4),
            "by_method": by_method,
        }

    async def get_best_performing_strategies(self, user_id: PydanticObjectId) -> dict:
        """Identify which strategies get best response rates."""
        trackers = await self._tracker_repo.get_for_user(user_id=user_id, limit=_MAX_TRACKERS_FETCH)
        strategy_stats: dict[str, dict] = {}
        for t in trackers:
            strategy = t.resume_strategy
            if not strategy:
                continue
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"total": 0, "responded": 0}
            strategy_stats[strategy]["total"] += 1
            if t.outcome_status in _RESPONDED_STATUSES:
                strategy_stats[strategy]["responded"] += 1

        ranked = sorted(
            [
                {
                    "strategy": k,
                    "total": v["total"],
                    "rate": round(v["responded"] / v["total"], 4) if v["total"] else 0.0,
                }
                for k, v in strategy_stats.items()
            ],
            key=lambda x: x["rate"],
            reverse=True,
        )
        return {"strategies": ranked}

    async def get_avg_response_time(self, user_id: PydanticObjectId) -> dict:
        """Placeholder for average response time — needs transition timestamps."""
        return {"avg_days": None, "sample_size": 0}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def confidence_level(sample_size: int) -> str:
    """Return confidence indicator based on sample size."""
    if sample_size < 5:
        return "insufficient"
    if sample_size < 15:
        return "low"
    if sample_size < 30:
        return "moderate"
    return "high"


def _group_by_strategy(trackers: list, field: str) -> list[dict]:
    """Group trackers by a strategy field, return ranked list."""
    stats: dict[str, dict] = {}
    for t in trackers:
        val = getattr(t, field, "") or ""
        if not val:
            continue
        if val not in stats:
            stats[val] = {"total": 0, "responded": 0}
        stats[val]["total"] += 1
        if t.outcome_status in _RESPONDED_STATUSES:
            stats[val]["responded"] += 1

    return sorted(
        [
            {
                "strategy": k,
                "sample_size": v["total"],
                "response_rate": round(v["responded"] / v["total"], 4) if v["total"] else 0.0,
            }
            for k, v in stats.items()
        ],
        key=lambda x: x["response_rate"],
        reverse=True,
    )
