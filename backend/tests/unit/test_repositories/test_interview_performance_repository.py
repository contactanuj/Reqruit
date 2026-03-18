"""Tests for InterviewPerformanceRepository."""

from unittest.mock import AsyncMock

from beanie import PydanticObjectId

from src.db.documents.interview_performance import InterviewPerformance
from src.repositories.interview_performance_repository import (
    InterviewPerformanceRepository,
)


class TestInterviewPerformanceRepository:
    """Tests for InterviewPerformanceRepository domain methods."""

    def test_init(self) -> None:
        repo = InterviewPerformanceRepository()
        assert repo._model is InterviewPerformance

    async def test_get_by_session_found(self) -> None:
        repo = InterviewPerformanceRepository()
        user_id = PydanticObjectId()
        session_id = "test-session-1"
        mock_perf = InterviewPerformance(user_id=user_id, session_id=session_id)
        repo.find_one = AsyncMock(return_value=mock_perf)

        result = await repo.get_by_session(user_id, session_id)

        assert result is mock_perf
        repo.find_one.assert_called_once_with(
            {"user_id": user_id, "session_id": session_id}
        )

    async def test_get_by_session_not_found(self) -> None:
        repo = InterviewPerformanceRepository()
        user_id = PydanticObjectId()
        repo.find_one = AsyncMock(return_value=None)

        result = await repo.get_by_session(user_id, "nonexistent")

        assert result is None

    async def test_get_user_sessions(self) -> None:
        repo = InterviewPerformanceRepository()
        user_id = PydanticObjectId()
        mock_sessions = [
            InterviewPerformance(user_id=user_id, session_id="s1"),
            InterviewPerformance(user_id=user_id, session_id="s2"),
        ]
        repo.find_many = AsyncMock(return_value=mock_sessions)

        result = await repo.get_user_sessions(user_id, limit=10)

        assert len(result) == 2
        repo.find_many.assert_called_once_with(
            {"user_id": user_id},
            sort="-created_at",
            skip=0,
            limit=10,
        )

    async def test_get_user_sessions_by_type(self) -> None:
        repo = InterviewPerformanceRepository()
        user_id = PydanticObjectId()
        repo.find_many = AsyncMock(return_value=[])

        await repo.get_user_sessions_by_type(user_id, "behavioral")

        repo.find_many.assert_called_once_with(
            {"user_id": user_id, "question_scores.question_type": "behavioral"},
            sort="-created_at",
        )

    async def test_inherits_base_repository_methods(self) -> None:
        repo = InterviewPerformanceRepository()
        assert hasattr(repo, "create")
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "find_many")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")
        assert hasattr(repo, "count")
