"""
Outcome service — transition validation and tracker creation/update orchestration.

Business logic for recording application outcomes. Validates status transitions
against the state machine, creates or updates ApplicationSuccessTracker documents,
and auto-populates metadata from Application Phase 2 fields when available.
"""

from datetime import datetime

import structlog
from beanie import PydanticObjectId

from src.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from src.db.documents.application_success_tracker import ApplicationSuccessTracker
from src.db.documents.enums import OutcomeStatus, VALID_TRANSITIONS
from src.repositories.application_repository import ApplicationRepository
from src.repositories.success_tracker_repository import ApplicationSuccessTrackerRepository

logger = structlog.get_logger()


class OutcomeService:
    """Orchestrates outcome recording with transition validation."""

    def __init__(
        self,
        tracker_repo: ApplicationSuccessTrackerRepository,
        app_repo: ApplicationRepository,
    ) -> None:
        self._tracker_repo = tracker_repo
        self._app_repo = app_repo

    def validate_transition(
        self, current_status: OutcomeStatus | None, new_status: OutcomeStatus
    ) -> None:
        """Validate that the transition is allowed by the state machine.

        Raises BusinessValidationError with INVALID_STATUS_TRANSITION if invalid.
        """
        if current_status is None:
            # Initial status must be APPLIED
            if new_status != OutcomeStatus.APPLIED:
                raise BusinessValidationError(
                    detail=f"Initial outcome status must be 'applied', got '{new_status}'",
                    error_code="INVALID_STATUS_TRANSITION",
                )
            return

        allowed = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise BusinessValidationError(
                detail=f"Cannot transition from '{current_status}' to '{new_status}'",
                error_code="INVALID_STATUS_TRANSITION",
            )

    def build_transition(
        self, previous_status: OutcomeStatus | None, new_status: OutcomeStatus
    ) -> dict:
        """Create a timestamped transition record."""
        return {
            "previous_status": str(previous_status) if previous_status else None,
            "new_status": str(new_status),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def create_or_update_tracker(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId,
        new_status: OutcomeStatus,
        submission_method: str | None = None,
        resume_strategy: str | None = None,
        cover_letter_strategy: str | None = None,
    ) -> ApplicationSuccessTracker:
        """Create a new tracker or update an existing one.

        Auto-populates metadata from Application Phase 2 fields when creating.
        Uses atomic update for concurrent safety when updating.
        """
        # Verify application exists and belongs to user
        application = await self._app_repo.get_by_user_and_id(user_id, application_id)
        if not application:
            raise NotFoundError("Application", str(application_id))

        # Check for existing tracker
        existing = await self._tracker_repo.get_by_application(user_id, application_id)

        if existing:
            # Update existing tracker
            self.validate_transition(existing.outcome_status, new_status)
            transition = self.build_transition(existing.outcome_status, new_status)

            updated = await self._tracker_repo.atomic_status_update(
                user_id=user_id,
                application_id=application_id,
                expected_status=existing.outcome_status,
                new_status=new_status,
                transition=transition,
            )

            if not updated:
                raise ConflictError(
                    detail="Concurrent update detected — status changed since read",
                    error_code="CONCURRENT_UPDATE_CONFLICT",
                )

            logger.info(
                "outcome_updated",
                user_id=str(user_id),
                application_id=str(application_id),
                previous_status=str(existing.outcome_status),
                new_status=str(new_status),
            )
            return updated

        # Create new tracker
        self.validate_transition(None, new_status)
        transition = self.build_transition(None, new_status)

        tracker = ApplicationSuccessTracker(
            user_id=user_id,
            application_id=application_id,
            outcome_status=new_status,
            outcome_transitions=[transition],
            resume_version_used=application.resume_version_used,
            cover_letter_version=application.cover_letter_version,
            submission_method=submission_method or application.submission_method,
            resume_strategy=resume_strategy or application.tailoring_strategy,
            cover_letter_strategy=cover_letter_strategy or "",
            submitted_at=application.applied_at or datetime.utcnow(),
            last_updated=datetime.utcnow(),
        )

        created = await self._tracker_repo.create(tracker)

        logger.info(
            "tracker_created",
            user_id=str(user_id),
            application_id=str(application_id),
            outcome_status=str(new_status),
        )
        return created

    async def list_trackers(
        self,
        user_id: PydanticObjectId,
        filters: dict | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ApplicationSuccessTracker]:
        """List outcome trackers for a user with optional filters."""
        return await self._tracker_repo.get_for_user(
            user_id=user_id,
            filters=filters if filters else None,
            skip=skip,
            limit=limit,
        )
