"""Tests for NudgeEngine — timing-based nudge evaluation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.db.documents.nudge import NudgeStatus, NudgeType
from src.services.nudge_engine import (
    FOLLOW_UP_DAYS,
    GHOST_APPLIED_DAYS,
    GHOST_INTERVIEWING_DAYS,
    OUTCOME_CHECK_DAYS,
    SECOND_FOLLOW_UP_DAYS,
    NudgeEngine,
)

USER_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
APP_ID = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


def _make_engine(create_return=None, find_one_return=None):
    nudge_repo = MagicMock()
    nudge_repo.create_if_not_exists = AsyncMock(return_value=create_return)
    nudge_repo.find_one = AsyncMock(return_value=find_one_return)
    integration_repo = MagicMock()
    engine = NudgeEngine(nudge_repo, integration_repo)
    return engine, nudge_repo


def _make_nudge(nudge_type=NudgeType.FOLLOW_UP_REMINDER):
    nudge = MagicMock()
    nudge.nudge_type = nudge_type
    nudge.status = NudgeStatus.PENDING
    return nudge


class TestTerminalStatuses:
    async def test_rejected_generates_no_nudges(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "rejected", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=30),
        )
        assert result == []

    async def test_offer_received_generates_no_nudges(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "offer_received", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=30),
        )
        assert result == []

    async def test_archived_generates_no_nudges(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "archived", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=30),
        )
        assert result == []

    async def test_withdrawn_generates_no_nudges(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "withdrawn", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=30),
        )
        assert result == []


class TestFollowUpReminder:
    async def test_generates_after_threshold(self):
        nudge = _make_nudge()
        engine, repo = _make_engine(create_return=nudge)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=FOLLOW_UP_DAYS + 1),
        )
        assert nudge in result
        repo.create_if_not_exists.assert_awaited()

    async def test_no_nudge_before_threshold(self):
        engine, repo = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=FOLLOW_UP_DAYS - 1),
        )
        assert result == []

    async def test_idempotent_returns_none_for_existing(self):
        engine, repo = _make_engine(create_return=None)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=FOLLOW_UP_DAYS + 1),
        )
        assert len(result) == 0


class TestSecondFollowUp:
    async def test_generates_when_first_exists(self):
        first_nudge = _make_nudge(NudgeType.FOLLOW_UP_REMINDER)
        second_nudge = _make_nudge(NudgeType.SECOND_FOLLOW_UP)
        engine, repo = _make_engine(
            create_return=second_nudge, find_one_return=first_nudge
        )
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=SECOND_FOLLOW_UP_DAYS + 1),
        )
        assert second_nudge in result

    async def test_skipped_when_first_missing(self):
        engine, repo = _make_engine(create_return=None, find_one_return=None)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=SECOND_FOLLOW_UP_DAYS + 1),
        )
        # No second follow-up because first doesn't exist
        assert len(result) == 0

    async def test_not_generated_before_threshold(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=SECOND_FOLLOW_UP_DAYS - 1),
        )
        # Only follow-up reminder possible (at 7+ days), not second
        assert all(
            getattr(n, "nudge_type", None) != NudgeType.SECOND_FOLLOW_UP
            for n in result
        )


class TestGhostApplied:
    async def test_generates_after_threshold(self):
        nudge = _make_nudge(NudgeType.GHOST_WARNING)
        engine, _ = _make_engine(create_return=nudge)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=GHOST_APPLIED_DAYS + 1),
        )
        assert nudge in result

    async def test_no_ghost_before_threshold(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "applied", "Acme", "SWE",
            last_updated=datetime.now(UTC) - timedelta(days=GHOST_APPLIED_DAYS - 1),
        )
        ghost_nudges = [
            n for n in result
            if getattr(n, "nudge_type", None) == NudgeType.GHOST_WARNING
        ]
        assert len(ghost_nudges) == 0


class TestOutcomeCheck:
    async def test_generates_after_interview(self):
        nudge = _make_nudge(NudgeType.OUTCOME_CHECK)
        engine, _ = _make_engine(create_return=nudge)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "interviewing", "Acme", "SWE",
            last_updated=datetime.now(UTC),
            last_interview_date=datetime.now(UTC) - timedelta(days=OUTCOME_CHECK_DAYS + 1),
        )
        assert nudge in result

    async def test_no_nudge_without_interview_date(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "interviewing", "Acme", "SWE",
            last_updated=datetime.now(UTC),
            last_interview_date=None,
        )
        assert result == []

    async def test_no_nudge_before_threshold(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "interviewing", "Acme", "SWE",
            last_updated=datetime.now(UTC),
            last_interview_date=datetime.now(UTC) - timedelta(days=OUTCOME_CHECK_DAYS - 1),
        )
        assert result == []


class TestGhostInterviewing:
    async def test_generates_after_threshold(self):
        nudge = _make_nudge(NudgeType.GHOST_WARNING)
        engine, _ = _make_engine(create_return=nudge)
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "interviewing", "Acme", "SWE",
            last_updated=datetime.now(UTC),
            last_interview_date=datetime.now(UTC) - timedelta(days=GHOST_INTERVIEWING_DAYS + 1),
        )
        assert nudge in result

    async def test_no_ghost_before_threshold(self):
        engine, _ = _make_engine()
        result = await engine.evaluate_application(
            USER_ID, APP_ID, "interviewing", "Acme", "SWE",
            last_updated=datetime.now(UTC),
            last_interview_date=datetime.now(UTC) - timedelta(days=GHOST_INTERVIEWING_DAYS - 1),
        )
        assert result == []


class TestHasIntegrations:
    async def test_returns_true_when_connected(self):
        conn = MagicMock()
        conn.status.value = "connected"
        integration_repo = MagicMock()
        integration_repo.get_all_by_user = AsyncMock(return_value=[conn])
        engine = NudgeEngine(MagicMock(), integration_repo)
        assert await engine.has_integrations(USER_ID) is True

    async def test_returns_false_when_none_connected(self):
        conn = MagicMock()
        conn.status.value = "disconnected"
        integration_repo = MagicMock()
        integration_repo.get_all_by_user = AsyncMock(return_value=[conn])
        engine = NudgeEngine(MagicMock(), integration_repo)
        assert await engine.has_integrations(USER_ID) is False

    async def test_returns_false_without_integration_repo(self):
        engine = NudgeEngine(MagicMock(), None)
        assert await engine.has_integrations(USER_ID) is False


class TestBuildNudgeMessage:
    def test_follow_up_message(self):
        from src.services.nudge_engine import _build_nudge_message

        title, message, actions = _build_nudge_message(
            NudgeType.FOLLOW_UP_REMINDER, "Acme", "SWE", 7
        )
        assert "Acme" in title
        assert "7 days" in message
        assert len(actions) == 3

    def test_second_follow_up_message(self):
        from src.services.nudge_engine import _build_nudge_message

        title, message, actions = _build_nudge_message(
            NudgeType.SECOND_FOLLOW_UP, "Acme", "SWE", 14
        )
        assert "Acme" in title
        assert len(actions) == 2

    def test_outcome_check_message(self):
        from src.services.nudge_engine import _build_nudge_message

        title, message, actions = _build_nudge_message(
            NudgeType.OUTCOME_CHECK, "Acme", "SWE", 3
        )
        assert "interview" in title.lower()
        assert len(actions) == 3

    def test_ghost_warning_message(self):
        from src.services.nudge_engine import _build_nudge_message

        title, message, actions = _build_nudge_message(
            NudgeType.GHOST_WARNING, "Acme", "SWE", 21
        )
        assert "ghosted" in title.lower()
        assert len(actions) == 3

    def test_unknown_type_fallback(self):
        from src.services.nudge_engine import _build_nudge_message

        title, message, actions = _build_nudge_message(
            "unknown_type", "Acme", "SWE", 5
        )
        assert "update" in title.lower()
        assert len(actions) == 1
