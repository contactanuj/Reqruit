"""Tests for UserActivity document model."""

from datetime import UTC, datetime

from src.db.documents.user_activity import ActivityEntry, UserActivity


class TestActivityEntry:
    def test_defaults(self):
        entry = ActivityEntry(action_type="job_saved")
        assert entry.action_type == "job_saved"
        assert entry.xp_earned == 0
        assert entry.metadata == {}
        assert entry.timestamp is not None

    def test_with_xp(self):
        entry = ActivityEntry(action_type="application_submitted", xp_earned=30)
        assert entry.xp_earned == 30

    def test_with_metadata(self):
        entry = ActivityEntry(
            action_type="job_saved", metadata={"job_id": "abc"}
        )
        assert entry.metadata["job_id"] == "abc"


class TestUserActivity:
    def test_settings_name(self):
        assert UserActivity.Settings.name == "user_activities"

    def test_defaults(self):
        from beanie import PydanticObjectId

        doc = UserActivity(
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
            date=datetime.now(UTC),
        )
        assert doc.actions == []
        assert doc.streak_count == 0
        assert doc.total_xp == 0
        assert doc.current_league == "bronze"
        assert doc.streak_freeze_available is True

    def test_compound_index_defined(self):
        indexes = UserActivity.Settings.indexes
        assert len(indexes) >= 1
        keys = indexes[0].document["key"]
        assert "user_id" in keys
        assert "date" in keys

    def test_registered_in_all_models(self):
        from src.db.documents import ALL_DOCUMENT_MODELS

        assert UserActivity in ALL_DOCUMENT_MODELS
