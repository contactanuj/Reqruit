"""
Interview performance repository — owner-scoped CRUD for session performance records.

All queries are scoped to a user_id for ownership enforcement.
"""

from beanie import PydanticObjectId

from src.db.documents.interview_performance import InterviewPerformance, QuestionScore
from src.repositories.base import BaseRepository


def _question_score_avg(qs: QuestionScore) -> float:
    """Average of the 4 scoring dimensions for a single question."""
    vals = [qs.score_relevance, qs.score_structure,
            qs.score_specificity, qs.score_confidence]
    non_zero = [v for v in vals if v > 0]
    return sum(non_zero) / len(non_zero) if non_zero else 0.0


def _category_averages(sessions: list[InterviewPerformance]) -> dict[str, float]:
    """Compute average scores per question_type across a list of sessions."""
    cat_scores: dict[str, list[float]] = {}
    for session in sessions:
        for qs in session.question_scores:
            qtype = qs.question_type or "unknown"
            cat_scores.setdefault(qtype, []).append(_question_score_avg(qs))
    return {
        cat: sum(scores) / len(scores) if scores else 0.0
        for cat, scores in cat_scores.items()
    }


class InterviewPerformanceRepository(BaseRepository[InterviewPerformance]):
    """InterviewPerformance-specific data access methods."""

    def __init__(self) -> None:
        super().__init__(InterviewPerformance)

    async def get_by_session(
        self, user_id: PydanticObjectId, session_id: str
    ) -> InterviewPerformance | None:
        """Fetch a specific session by user and session_id."""
        return await self.find_one({"user_id": user_id, "session_id": session_id})

    async def get_user_sessions(
        self, user_id: PydanticObjectId, skip: int = 0, limit: int = 20
    ) -> list[InterviewPerformance]:
        """Get recent sessions for a user, ordered by most recent first."""
        return await self.find_many(
            {"user_id": user_id},
            sort="-created_at",
            skip=skip,
            limit=limit,
        )

    async def get_user_sessions_by_type(
        self, user_id: PydanticObjectId, question_type: str
    ) -> list[InterviewPerformance]:
        """Get sessions containing questions of a specific type."""
        return await self.find_many(
            {"user_id": user_id, "question_scores.question_type": question_type},
            sort="-created_at",
        )

    async def count_active_sessions(self, user_id: PydanticObjectId) -> int:
        """Count sessions without a session_summary (not yet completed/debriefed)."""
        return await self.count(
            {"user_id": user_id, "session_summary": {"$in": [None, ""]}}
        )

    async def count_user_sessions(self, user_id: PydanticObjectId) -> int:
        """Count all sessions for a user."""
        return await self.count({"user_id": user_id})

    async def get_user_trends(
        self, user_id: PydanticObjectId, sessions: list[InterviewPerformance] | None = None
    ) -> dict:
        """Compute per-category score trends across all sessions."""
        if sessions is None:
            sessions = await self.get_user_sessions(user_id, limit=100)
        if not sessions:
            return {"categories": {}, "overall_trend": []}

        category_scores: dict[str, list[dict]] = {}
        overall_trend = []

        for session in sessions:
            overall_trend.append({
                "session_id": session.session_id,
                "overall_score": session.overall_score,
                "created_at": str(session.created_at) if session.created_at else None,
            })
            for qs in session.question_scores:
                qtype = qs.question_type or "unknown"
                avg = _question_score_avg(qs)
                category_scores.setdefault(qtype, []).append({
                    "session_id": session.session_id,
                    "score": avg,
                    "created_at": str(session.created_at) if session.created_at else None,
                })

        categories = {}
        for cat, entries in category_scores.items():
            avg = sum(e["score"] for e in entries) / len(entries) if entries else 0.0
            categories[cat] = {
                "average_score": round(avg, 2),
                "data_points": len(entries),
                "trend": entries,
            }

        return {"categories": categories, "overall_trend": overall_trend}

    async def get_improvement_velocity(
        self, user_id: PydanticObjectId, sessions: list[InterviewPerformance] | None = None
    ) -> dict:
        """Compare first half vs second half of sessions per category."""
        if sessions is None:
            sessions = await self.get_user_sessions(user_id, limit=100)
        if len(sessions) < 2:
            return {"velocity": {}, "has_enough_data": False}

        # Sessions are newest-first; reverse for chronological order
        chronological = list(reversed(sessions))
        mid = len(chronological) // 2
        early = chronological[:mid]
        late = chronological[mid:]

        early_avgs = _category_averages(early)
        late_avgs = _category_averages(late)

        velocity = {}
        all_cats = set(early_avgs.keys()) | set(late_avgs.keys())
        for cat in sorted(all_cats):
            e = early_avgs.get(cat, 0.0)
            la = late_avgs.get(cat, 0.0)
            velocity[cat] = {
                "early_avg": round(e, 2),
                "late_avg": round(la, 2),
                "delta": round(la - e, 2),
                "improving": la > e,
            }

        return {"velocity": velocity, "has_enough_data": True}

    async def get_weak_areas(
        self, user_id: PydanticObjectId, threshold: float = 3.0,
        sessions: list[InterviewPerformance] | None = None,
    ) -> list[dict]:
        """Find categories with scores consistently below threshold across 3+ sessions."""
        if sessions is None:
            sessions = await self.get_user_sessions(user_id, limit=100)
        if len(sessions) < 3:
            return []

        category_weak_sessions: dict[str, list[dict]] = {}
        for session in sessions:
            cat_scores: dict[str, list[float]] = {}
            for qs in session.question_scores:
                qtype = qs.question_type or "unknown"
                cat_scores.setdefault(qtype, []).append(_question_score_avg(qs))

            for cat, scores in cat_scores.items():
                cat_avg = sum(scores) / len(scores)
                if cat_avg < threshold:
                    category_weak_sessions.setdefault(cat, []).append({
                        "session_id": session.session_id,
                        "avg_score": round(cat_avg, 2),
                    })

        recurring = []
        for cat, weak_sessions in category_weak_sessions.items():
            if len(weak_sessions) >= 3:
                recurring.append({
                    "category": cat,
                    "weak_session_count": len(weak_sessions),
                    "average_score": round(
                        sum(w["avg_score"] for w in weak_sessions) / len(weak_sessions), 2
                    ),
                    "examples": weak_sessions[:5],
                })

        return sorted(recurring, key=lambda x: x["average_score"])
