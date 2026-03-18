"""
Tests for the OutcomeService — transition validation and tracker orchestration.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.enums import OutcomeStatus
from src.services.outcome_service import OutcomeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(tracker_repo=None, app_repo=None):
    return OutcomeService(
        tracker_repo=tracker_repo or MagicMock(),
        app_repo=app_repo or MagicMock(),
    )


_user_id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
_app_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------


class TestValidateTransition:
    def test_valid_applied_to_viewed(self) -> None:
        svc = _make_service()
        svc.validate_transition(OutcomeStatus.APPLIED, OutcomeStatus.VIEWED)

    def test_valid_skip_ahead_applied_to_interview(self) -> None:
        svc = _make_service()
        svc.validate_transition(OutcomeStatus.APPLIED, OutcomeStatus.INTERVIEW_SCHEDULED)

    def test_valid_viewed_to_responded(self) -> None:
        svc = _make_service()
        svc.validate_transition(OutcomeStatus.VIEWED, OutcomeStatus.RESPONDED)

    def test_valid_interview_to_offer(self) -> None:
        svc = _make_service()
        svc.validate_transition(OutcomeStatus.INTERVIEW_SCHEDULED, OutcomeStatus.OFFER_RECEIVED)

    def test_invalid_offer_to_applied(self) -> None:
        svc = _make_service()
        with pytest.raises(BusinessValidationError) as exc_info:
            svc.validate_transition(OutcomeStatus.OFFER_RECEIVED, OutcomeStatus.APPLIED)
        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    def test_invalid_rejected_terminal(self) -> None:
        svc = _make_service()
        with pytest.raises(BusinessValidationError) as exc_info:
            svc.validate_transition(OutcomeStatus.REJECTED, OutcomeStatus.VIEWED)
        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    def test_invalid_ghosted_terminal(self) -> None:
        svc = _make_service()
        with pytest.raises(BusinessValidationError) as exc_info:
            svc.validate_transition(OutcomeStatus.GHOSTED, OutcomeStatus.RESPONDED)
        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    def test_initial_must_be_applied(self) -> None:
        svc = _make_service()
        with pytest.raises(BusinessValidationError) as exc_info:
            svc.validate_transition(None, OutcomeStatus.VIEWED)
        assert exc_info.value.error_code == "INVALID_STATUS_TRANSITION"

    def test_initial_applied_valid(self) -> None:
        svc = _make_service()
        svc.validate_transition(None, OutcomeStatus.APPLIED)


# ---------------------------------------------------------------------------
# build_transition
# ---------------------------------------------------------------------------


class TestBuildTransition:
    def test_initial_transition(self) -> None:
        svc = _make_service()
        t = svc.build_transition(None, OutcomeStatus.APPLIED)
        assert t["previous_status"] is None
        assert t["new_status"] == "applied"
        assert "timestamp" in t

    def test_update_transition(self) -> None:
        svc = _make_service()
        t = svc.build_transition(OutcomeStatus.APPLIED, OutcomeStatus.VIEWED)
        assert t["previous_status"] == "applied"
        assert t["new_status"] == "viewed"


# ---------------------------------------------------------------------------
# create_or_update_tracker
# ---------------------------------------------------------------------------


class TestCreateOrUpdateTracker:
    async def test_create_new_tracker(self) -> None:
        app = MagicMock()
        app.resume_version_used = 1
        app.cover_letter_version = 2
        app.submission_method = "linkedin"
        app.tailoring_strategy = "keyword_focused"
        app.applied_at = None

        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=app)

        tracker_repo = MagicMock()
        tracker_repo.get_by_application = AsyncMock(return_value=None)
        created = MagicMock()
        created.id = PydanticObjectId("cccccccccccccccccccccccc")
        tracker_repo.create = AsyncMock(return_value=created)

        svc = _make_service(tracker_repo=tracker_repo, app_repo=app_repo)
        result = await svc.create_or_update_tracker(
            user_id=_user_id,
            application_id=_app_id,
            new_status=OutcomeStatus.APPLIED,
        )

        tracker_repo.create.assert_called_once()
        assert result == created

    async def test_update_existing_tracker(self) -> None:
        app = MagicMock()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=app)

        existing = MagicMock()
        existing.outcome_status = OutcomeStatus.APPLIED

        tracker_repo = MagicMock()
        tracker_repo.get_by_application = AsyncMock(return_value=existing)
        updated = MagicMock()
        tracker_repo.atomic_status_update = AsyncMock(return_value=updated)

        svc = _make_service(tracker_repo=tracker_repo, app_repo=app_repo)
        result = await svc.create_or_update_tracker(
            user_id=_user_id,
            application_id=_app_id,
            new_status=OutcomeStatus.VIEWED,
        )

        tracker_repo.atomic_status_update.assert_called_once()
        assert result == updated

    async def test_app_not_found_raises_404(self) -> None:
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=None)

        svc = _make_service(app_repo=app_repo)
        with pytest.raises(NotFoundError):
            await svc.create_or_update_tracker(
                user_id=_user_id,
                application_id=_app_id,
                new_status=OutcomeStatus.APPLIED,
            )

    async def test_concurrent_update_raises_conflict(self) -> None:
        app = MagicMock()
        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=app)

        existing = MagicMock()
        existing.outcome_status = OutcomeStatus.APPLIED

        tracker_repo = MagicMock()
        tracker_repo.get_by_application = AsyncMock(return_value=existing)
        tracker_repo.atomic_status_update = AsyncMock(return_value=None)

        svc = _make_service(tracker_repo=tracker_repo, app_repo=app_repo)
        with pytest.raises(ConflictError):
            await svc.create_or_update_tracker(
                user_id=_user_id,
                application_id=_app_id,
                new_status=OutcomeStatus.VIEWED,
            )

    async def test_auto_populates_from_application(self) -> None:
        app = MagicMock()
        app.resume_version_used = 3
        app.cover_letter_version = 1
        app.submission_method = "email"
        app.tailoring_strategy = "referral"
        app.applied_at = None

        app_repo = MagicMock()
        app_repo.get_by_user_and_id = AsyncMock(return_value=app)

        tracker_repo = MagicMock()
        tracker_repo.get_by_application = AsyncMock(return_value=None)
        tracker_repo.create = AsyncMock(side_effect=lambda t: t)

        svc = _make_service(tracker_repo=tracker_repo, app_repo=app_repo)
        result = await svc.create_or_update_tracker(
            user_id=_user_id,
            application_id=_app_id,
            new_status=OutcomeStatus.APPLIED,
        )

        assert result.resume_version_used == 3
        assert result.submission_method == "email"
        assert result.resume_strategy == "referral"
