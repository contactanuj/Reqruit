"""
Tests for ApplicationSuccessTrackerRepository.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId

from src.db.documents.enums import OutcomeStatus
from src.repositories.success_tracker_repository import ApplicationSuccessTrackerRepository


_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
_app_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


class TestGetByApplication:
    async def test_calls_find_one_with_correct_filters(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        with patch.object(repo, "find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            await repo.get_by_application(_user_id, _app_id)
            mock_find.assert_called_once_with(
                {"user_id": _user_id, "application_id": _app_id}
            )


class TestAtomicStatusUpdate:
    async def test_calls_find_one_and_update(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        transition = {"previous_status": "applied", "new_status": "viewed", "timestamp": "2026-03-14"}

        with patch(
            "src.repositories.success_tracker_repository.ApplicationSuccessTracker"
        ) as mock_cls:
            mock_cls.find_one_and_update = AsyncMock(return_value=MagicMock())
            result = await repo.atomic_status_update(
                user_id=_user_id,
                application_id=_app_id,
                expected_status=OutcomeStatus.APPLIED,
                new_status=OutcomeStatus.VIEWED,
                transition=transition,
            )

            mock_cls.find_one_and_update.assert_called_once()
            call_args = mock_cls.find_one_and_update.call_args
            filter_arg = call_args[0][0]
            assert filter_arg["user_id"] == _user_id
            assert filter_arg["application_id"] == _app_id
            assert filter_arg["outcome_status"] == OutcomeStatus.APPLIED
            assert result is not None

    async def test_returns_none_on_precondition_failure(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        transition = {"previous_status": "applied", "new_status": "viewed", "timestamp": "2026-03-14"}

        with patch(
            "src.repositories.success_tracker_repository.ApplicationSuccessTracker"
        ) as mock_cls:
            mock_cls.find_one_and_update = AsyncMock(return_value=None)
            result = await repo.atomic_status_update(
                user_id=_user_id,
                application_id=_app_id,
                expected_status=OutcomeStatus.APPLIED,
                new_status=OutcomeStatus.VIEWED,
                transition=transition,
            )
            assert result is None


class TestAggregateSummary:
    async def test_calls_aggregate_with_pipeline(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        with patch(
            "src.repositories.success_tracker_repository.ApplicationSuccessTracker"
        ) as mock_cls:
            mock_agg = MagicMock()
            mock_agg.to_list = AsyncMock(return_value=[{"total": [{"count": 5}]}])
            mock_cls.aggregate = MagicMock(return_value=mock_agg)

            result = await repo.aggregate_summary(_user_id)

            mock_cls.aggregate.assert_called_once()
            pipeline = mock_cls.aggregate.call_args[0][0]
            assert pipeline[0] == {"$match": {"user_id": _user_id}}
            assert "$facet" in pipeline[1]
            assert result == {"total": [{"count": 5}]}

    async def test_returns_empty_dict_when_no_results(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        with patch(
            "src.repositories.success_tracker_repository.ApplicationSuccessTracker"
        ) as mock_cls:
            mock_agg = MagicMock()
            mock_agg.to_list = AsyncMock(return_value=[])
            mock_cls.aggregate = MagicMock(return_value=mock_agg)

            result = await repo.aggregate_summary(_user_id)
            assert result == {}


class TestGetForUser:
    async def test_calls_find_many_with_user_id(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            await repo.get_for_user(_user_id)
            mock_find.assert_called_once_with(
                {"user_id": _user_id}, skip=0, limit=20, sort="-last_updated"
            )

    async def test_passes_filters(self) -> None:
        repo = ApplicationSuccessTrackerRepository()
        with patch.object(repo, "find_many", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            await repo.get_for_user(
                _user_id, filters={"outcome_status": "viewed"}, skip=10, limit=5
            )
            mock_find.assert_called_once_with(
                {"user_id": _user_id, "outcome_status": "viewed"},
                skip=10, limit=5, sort="-last_updated",
            )
