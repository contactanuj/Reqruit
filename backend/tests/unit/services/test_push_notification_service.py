"""Tests for PushNotificationService — subscriptions, preferences, delivery."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.services.push_notification_service import (
    DEFAULT_PREFERENCES,
    NotificationPayload,
    PushNotificationService,
)


def _make_repos():
    """Create mock subscription and preferences repositories."""
    sub_repo = AsyncMock()
    pref_repo = AsyncMock()
    return sub_repo, pref_repo


def _user_id() -> PydanticObjectId:
    return PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _user_id_2() -> PydanticObjectId:
    return PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")


class TestNotificationPayload:
    def test_to_dict(self):
        payload = NotificationPayload(title="Hello", body="World")
        d = payload.to_dict()
        assert d["title"] == "Hello"
        assert d["body"] == "World"
        assert d["category"] == "general"
        assert d["icon"] == "/static/icons/icon-192.png"

    def test_custom_fields(self):
        payload = NotificationPayload(
            title="T",
            body="B",
            category="interview_reminder",
            action_url="/interviews/123",
            icon="/custom.png",
        )
        d = payload.to_dict()
        assert d["category"] == "interview_reminder"
        assert d["action_url"] == "/interviews/123"
        assert d["icon"] == "/custom.png"


class TestRegisterSubscription:
    async def test_register_returns_confirmation(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.get_by_user.return_value = None
        sub_repo.create.return_value = MagicMock()
        svc = PushNotificationService(sub_repo, pref_repo)

        result = await svc.register_subscription(
            _user_id(), {"endpoint": "https://push.example.com", "keys": {"p256dh": "k"}}
        )
        assert result["status"] == "registered"
        assert result["user_id"] == str(_user_id())
        sub_repo.create.assert_awaited_once()

    async def test_register_overwrites_existing(self):
        sub_repo, pref_repo = _make_repos()
        existing = MagicMock()
        existing.set = AsyncMock()
        sub_repo.get_by_user.return_value = existing
        svc = PushNotificationService(sub_repo, pref_repo)

        await svc.register_subscription(
            _user_id(), {"endpoint": "new", "keys": {"p256dh": "k"}}
        )
        existing.set.assert_awaited_once()
        sub_repo.create.assert_not_awaited()


class TestUnregisterSubscription:
    async def test_unregister_existing(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.delete_by_user.return_value = 1
        svc = PushNotificationService(sub_repo, pref_repo)

        result = await svc.unregister_subscription(_user_id())
        assert result["status"] == "unregistered"
        sub_repo.delete_by_user.assert_awaited_once_with(_user_id())

    async def test_unregister_nonexistent(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.delete_by_user.return_value = 0
        svc = PushNotificationService(sub_repo, pref_repo)

        result = await svc.unregister_subscription(_user_id())
        assert result["status"] == "unregistered"


class TestPreferences:
    async def test_get_defaults_when_no_document(self):
        sub_repo, pref_repo = _make_repos()
        pref_repo.get_by_user.return_value = None
        svc = PushNotificationService(sub_repo, pref_repo)

        prefs = await svc.get_preferences(_user_id())
        assert prefs == DEFAULT_PREFERENCES

    async def test_get_stored_preferences(self):
        sub_repo, pref_repo = _make_repos()
        doc = MagicMock()
        doc.daily_shortlist = True
        doc.interview_reminder = True
        doc.application_update = True
        doc.offer_received = True
        doc.nudge = False
        doc.market_alert = True
        pref_repo.get_by_user.return_value = doc
        svc = PushNotificationService(sub_repo, pref_repo)

        prefs = await svc.get_preferences(_user_id())
        assert prefs["nudge"] is False
        assert prefs["market_alert"] is True

    async def test_update_preferences(self):
        sub_repo, pref_repo = _make_repos()
        doc = MagicMock()
        doc.daily_shortlist = True
        doc.interview_reminder = True
        doc.application_update = True
        doc.offer_received = True
        doc.nudge = False
        doc.market_alert = False
        pref_repo.upsert_by_user.return_value = doc
        svc = PushNotificationService(sub_repo, pref_repo)

        result = await svc.update_preferences(_user_id(), {"nudge": False})
        assert result["nudge"] is False
        assert result["daily_shortlist"] is True
        pref_repo.upsert_by_user.assert_awaited_once()

    async def test_update_preserves_existing(self):
        sub_repo, pref_repo = _make_repos()
        doc = MagicMock()
        doc.daily_shortlist = True
        doc.interview_reminder = True
        doc.application_update = True
        doc.offer_received = True
        doc.nudge = False
        doc.market_alert = True
        pref_repo.upsert_by_user.return_value = doc
        svc = PushNotificationService(sub_repo, pref_repo)

        result = await svc.update_preferences(_user_id(), {"market_alert": True})
        assert result["nudge"] is False
        assert result["market_alert"] is True


class TestSendNotification:
    async def test_send_to_subscribed_user(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.get_by_user.return_value = MagicMock()  # subscription exists
        pref_repo.get_by_user.return_value = None  # default prefs
        svc = PushNotificationService(sub_repo, pref_repo)

        payload = NotificationPayload(title="New Job", body="Check it out")
        result = await svc.send_notification(_user_id(), payload)
        assert result["status"] == "sent"
        assert result["payload"]["title"] == "New Job"

    async def test_skip_no_subscription(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.get_by_user.return_value = None
        svc = PushNotificationService(sub_repo, pref_repo)

        payload = NotificationPayload(title="T", body="B")
        result = await svc.send_notification(_user_id(), payload)
        assert result["status"] == "skipped"
        assert result["reason"] == "no_subscription"

    async def test_skip_opted_out(self):
        sub_repo, pref_repo = _make_repos()
        sub_repo.get_by_user.return_value = MagicMock()  # subscription exists
        doc = MagicMock()
        doc.daily_shortlist = True
        doc.interview_reminder = True
        doc.application_update = True
        doc.offer_received = True
        doc.nudge = True
        doc.market_alert = False
        pref_repo.get_by_user.return_value = doc
        svc = PushNotificationService(sub_repo, pref_repo)

        payload = NotificationPayload(title="T", body="B", category="market_alert")
        result = await svc.send_notification(_user_id(), payload)
        assert result["status"] == "skipped"
        assert result["reason"] == "opted_out"


class TestSendBulk:
    async def test_bulk_send(self):
        sub_repo, pref_repo = _make_repos()
        uid1, uid2, uid3 = _user_id(), _user_id_2(), PydanticObjectId("cccccccccccccccccccccccc")

        async def _get_by_user(user_id):
            if user_id in (uid1, uid2):
                return MagicMock()
            return None

        sub_repo.get_by_user.side_effect = _get_by_user
        pref_repo.get_by_user.return_value = None  # default prefs
        svc = PushNotificationService(sub_repo, pref_repo)

        payload = NotificationPayload(title="Bulk", body="Hello all")
        result = await svc.send_bulk([uid1, uid2, uid3], payload)
        assert result["total"] == 3
        assert result["sent"] == 2

    async def test_bulk_empty_list(self):
        sub_repo, pref_repo = _make_repos()
        svc = PushNotificationService(sub_repo, pref_repo)

        payload = NotificationPayload(title="T", body="B")
        result = await svc.send_bulk([], payload)
        assert result["total"] == 0
        assert result["sent"] == 0
