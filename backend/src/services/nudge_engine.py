"""
NudgeEngine — stateless evaluator for application follow-up reminders and ghost detection.

Given a user's applications and their timestamps, deterministically decides
which nudges should exist. The create_if_not_exists pattern ensures idempotency.
"""

from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId

from src.db.documents.nudge import Nudge, NudgeStatus, NudgeType
from src.repositories.integration_connection_repository import (
    IntegrationConnectionRepository,
)
from src.repositories.nudge_repository import NudgeRepository

logger = structlog.get_logger()

FOLLOW_UP_DAYS = 7
OUTCOME_CHECK_DAYS = 3
SECOND_FOLLOW_UP_DAYS = 14
GHOST_APPLIED_DAYS = 21
GHOST_INTERVIEWING_DAYS = 7

# Statuses that should not generate nudges
TERMINAL_STATUSES = {"rejected", "offer_received", "archived", "withdrawn"}


class NudgeEngine:
    """Evaluate applications and generate nudges based on timing rules."""

    def __init__(
        self,
        nudge_repo: NudgeRepository,
        integration_repo: IntegrationConnectionRepository | None = None,
    ) -> None:
        self._nudge_repo = nudge_repo
        self._integration_repo = integration_repo

    async def evaluate_application(
        self,
        user_id: PydanticObjectId,
        application_id: PydanticObjectId,
        status: str,
        company_name: str,
        role: str,
        last_updated: datetime,
        last_interview_date: datetime | None = None,
    ) -> list[Nudge]:
        """
        Evaluate a single application and generate applicable nudges.

        Returns list of newly created nudges (empty if none needed or all already exist).
        """
        if status in TERMINAL_STATUSES:
            return []

        nudges = []
        now = datetime.now(UTC)
        days_since_update = (now - last_updated).days

        if status == "applied":
            nudge = await self._check_follow_up(
                user_id, application_id, company_name, role, days_since_update
            )
            if nudge:
                nudges.append(nudge)

            nudge = await self._check_second_follow_up(
                user_id, application_id, company_name, role, days_since_update
            )
            if nudge:
                nudges.append(nudge)

            nudge = await self._check_ghost_applied(
                user_id, application_id, company_name, role, days_since_update
            )
            if nudge:
                nudges.append(nudge)

        elif status == "interviewing":
            if last_interview_date:
                days_since_interview = (now - last_interview_date).days
                nudge = await self._check_outcome(
                    user_id, application_id, company_name, role, days_since_interview
                )
                if nudge:
                    nudges.append(nudge)

                nudge = await self._check_ghost_interviewing(
                    user_id, application_id, company_name, role, days_since_interview
                )
                if nudge:
                    nudges.append(nudge)

        return nudges

    async def _check_follow_up(
        self, user_id, app_id, company, role, days_since_update
    ) -> Nudge | None:
        if days_since_update < FOLLOW_UP_DAYS:
            return None
        title, message, actions = _build_nudge_message(
            NudgeType.FOLLOW_UP_REMINDER, company, role, days_since_update
        )
        return await self._create_nudge(
            user_id, app_id, NudgeType.FOLLOW_UP_REMINDER, title, message, actions
        )

    async def _check_second_follow_up(
        self, user_id, app_id, company, role, days_since_update
    ) -> Nudge | None:
        if days_since_update < SECOND_FOLLOW_UP_DAYS:
            return None
        # Only create second follow-up if first already exists
        existing = await self._nudge_repo.find_one({
            "user_id": user_id,
            "application_id": app_id,
            "nudge_type": NudgeType.FOLLOW_UP_REMINDER,
        })
        if existing is None:
            return None
        title, message, actions = _build_nudge_message(
            NudgeType.SECOND_FOLLOW_UP, company, role, days_since_update
        )
        return await self._create_nudge(
            user_id, app_id, NudgeType.SECOND_FOLLOW_UP, title, message, actions
        )

    async def _check_ghost_applied(
        self, user_id, app_id, company, role, days_since_update
    ) -> Nudge | None:
        if days_since_update < GHOST_APPLIED_DAYS:
            return None
        title, message, actions = _build_nudge_message(
            NudgeType.GHOST_WARNING, company, role, days_since_update
        )
        return await self._create_nudge(
            user_id, app_id, NudgeType.GHOST_WARNING, title, message, actions
        )

    async def _check_outcome(
        self, user_id, app_id, company, role, days_since_interview
    ) -> Nudge | None:
        if days_since_interview < OUTCOME_CHECK_DAYS:
            return None
        title, message, actions = _build_nudge_message(
            NudgeType.OUTCOME_CHECK, company, role, days_since_interview
        )
        return await self._create_nudge(
            user_id, app_id, NudgeType.OUTCOME_CHECK, title, message, actions
        )

    async def _check_ghost_interviewing(
        self, user_id, app_id, company, role, days_since_interview
    ) -> Nudge | None:
        if days_since_interview < GHOST_INTERVIEWING_DAYS:
            return None
        title, message, actions = _build_nudge_message(
            NudgeType.GHOST_WARNING, company, role, days_since_interview
        )
        return await self._create_nudge(
            user_id, app_id, NudgeType.GHOST_WARNING, title, message, actions
        )

    async def _create_nudge(
        self, user_id, app_id, nudge_type, title, message, actions
    ) -> Nudge | None:
        nudge = Nudge(
            user_id=user_id,
            application_id=app_id,
            nudge_type=nudge_type,
            status=NudgeStatus.PENDING,
            title=title,
            message=message,
            suggested_actions=actions,
            trigger_date=datetime.now(UTC),
        )
        return await self._nudge_repo.create_if_not_exists(nudge)

    async def has_integrations(self, user_id: PydanticObjectId) -> bool:
        """Check if user has any CONNECTED integrations."""
        if self._integration_repo is None:
            return False
        connections = await self._integration_repo.get_all_by_user(user_id)
        return any(c.status.value == "connected" for c in connections)


def _build_nudge_message(
    nudge_type: str, company: str, role: str, days: int
) -> tuple[str, str, list[str]]:
    """Return (title, message, suggested_actions) for a nudge type."""
    if nudge_type == NudgeType.FOLLOW_UP_REMINDER:
        return (
            f"Time to follow up on {company}",
            f"It's been {days} days since you applied to {role} at {company}. "
            "Consider sending a follow-up email.",
            ["Send follow-up email", "Check application portal", "Mark as no response"],
        )
    if nudge_type == NudgeType.SECOND_FOLLOW_UP:
        return (
            f"Still no response from {company}",
            f"It's been {days} days since you applied. A second follow-up might help.",
            ["Send second follow-up", "Mark as no response"],
        )
    if nudge_type == NudgeType.OUTCOME_CHECK:
        return (
            "How did the interview go?",
            f"Your interview at {company} was {days} days ago. "
            "Record the outcome to keep your board accurate.",
            ["Record outcome", "Schedule follow-up", "Mark as waiting"],
        )
    if nudge_type == NudgeType.GHOST_WARNING:
        return (
            f"You may have been ghosted by {company}",
            f"It's been {days} days with no response from {company}. "
            "This is common — consider these next steps.",
            ["Send final follow-up", "Move on to other opportunities", "Mark as ghosted"],
        )
    return (
        "Application update needed",
        f"Your application at {company} for {role} may need attention.",
        ["Review application"],
    )
