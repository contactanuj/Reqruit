"""
Tests for application outcome tracking API routes.
"""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_outcome_service,
)
from src.core.exceptions import BusinessValidationError, NotFoundError
from src.db.documents.enums import OutcomeStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = MagicMock()
    user.id = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")
    user.email = "test@example.com"
    user.is_active = True
    return user


def _make_tracker(
    outcome_status=OutcomeStatus.APPLIED,
    transitions=None,
):
    tracker = MagicMock()
    tracker.id = PydanticObjectId("cccccccccccccccccccccccc")
    tracker.application_id = PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")
    tracker.outcome_status = outcome_status
    tracker.outcome_transitions = transitions or [
        {"previous_status": None, "new_status": "applied", "timestamp": "2026-03-14T00:00:00"}
    ]
    tracker.resume_version_used = 1
    tracker.cover_letter_version = 1
    tracker.submission_method = "linkedin"
    tracker.resume_strategy = "keyword_focused"
    tracker.cover_letter_strategy = ""
    tracker.submitted_at = MagicMock(isoformat=lambda: "2026-03-14T00:00:00")
    tracker.last_updated = MagicMock(isoformat=lambda: "2026-03-14T00:00:00")
    return tracker


def _override(app, user, outcome_service):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_outcome_service] = lambda: outcome_service


# ---------------------------------------------------------------------------
# POST /applications/{id}/outcome
# ---------------------------------------------------------------------------


class TestRecordOutcome:
    async def test_record_outcome_200(self, client: AsyncClient) -> None:
        user = _make_user()
        tracker = _make_tracker()
        outcome_svc = MagicMock()
        outcome_svc.create_or_update_tracker = AsyncMock(return_value=tracker)
        _override(client.app, user, outcome_svc)

        response = await client.post(
            "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome",
            json={"outcome_status": "applied"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["outcome_status"] == "applied"
        assert data["application_id"] == "bbbbbbbbbbbbbbbbbbbbbbbb"

    async def test_record_outcome_update_200(self, client: AsyncClient) -> None:
        user = _make_user()
        tracker = _make_tracker(
            outcome_status=OutcomeStatus.VIEWED,
            transitions=[
                {"previous_status": None, "new_status": "applied", "timestamp": "2026-03-14T00:00:00"},
                {"previous_status": "applied", "new_status": "viewed", "timestamp": "2026-03-14T01:00:00"},
            ],
        )
        outcome_svc = MagicMock()
        outcome_svc.create_or_update_tracker = AsyncMock(return_value=tracker)
        _override(client.app, user, outcome_svc)

        response = await client.post(
            "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome",
            json={"outcome_status": "viewed"},
        )

        assert response.status_code == 200
        assert response.json()["outcome_status"] == "viewed"

    async def test_record_outcome_invalid_transition_422(self, client: AsyncClient) -> None:
        user = _make_user()
        outcome_svc = MagicMock()
        outcome_svc.create_or_update_tracker = AsyncMock(
            side_effect=BusinessValidationError(
                "Cannot transition", error_code="INVALID_STATUS_TRANSITION"
            )
        )
        _override(client.app, user, outcome_svc)

        response = await client.post(
            "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome",
            json={"outcome_status": "applied"},
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_STATUS_TRANSITION"

    async def test_record_outcome_app_not_found_404(self, client: AsyncClient) -> None:
        user = _make_user()
        outcome_svc = MagicMock()
        outcome_svc.create_or_update_tracker = AsyncMock(
            side_effect=NotFoundError("Application", "bbbbbbbbbbbbbbbbbbbbbbbb")
        )
        _override(client.app, user, outcome_svc)

        response = await client.post(
            "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome",
            json={"outcome_status": "applied"},
        )

        assert response.status_code == 404

    async def test_record_outcome_with_metadata(self, client: AsyncClient) -> None:
        user = _make_user()
        tracker = _make_tracker()
        outcome_svc = MagicMock()
        outcome_svc.create_or_update_tracker = AsyncMock(return_value=tracker)
        _override(client.app, user, outcome_svc)

        response = await client.post(
            "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome",
            json={
                "outcome_status": "applied",
                "submission_method": "email",
                "resume_strategy": "referral",
            },
        )

        assert response.status_code == 200
        outcome_svc.create_or_update_tracker.assert_called_once()
        call_kwargs = outcome_svc.create_or_update_tracker.call_args[1]
        assert call_kwargs["submission_method"] == "email"
        assert call_kwargs["resume_strategy"] == "referral"


# ---------------------------------------------------------------------------
# GET /applications/outcomes
# ---------------------------------------------------------------------------


class TestListOutcomes:
    async def test_list_outcomes_200(self, client: AsyncClient) -> None:
        user = _make_user()
        tracker = _make_tracker()
        outcome_svc = MagicMock()
        outcome_svc.list_trackers = AsyncMock(return_value=[tracker])
        _override(client.app, user, outcome_svc)

        response = await client.get("/applications/outcomes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["outcome_status"] == "applied"

    async def test_list_outcomes_with_filter(self, client: AsyncClient) -> None:
        user = _make_user()
        outcome_svc = MagicMock()
        outcome_svc.list_trackers = AsyncMock(return_value=[])
        _override(client.app, user, outcome_svc)

        response = await client.get("/applications/outcomes?status=viewed")

        assert response.status_code == 200
        outcome_svc.list_trackers.assert_called_once()

    async def test_list_outcomes_empty(self, client: AsyncClient) -> None:
        user = _make_user()
        outcome_svc = MagicMock()
        outcome_svc.list_trackers = AsyncMock(return_value=[])
        _override(client.app, user, outcome_svc)

        response = await client.get("/applications/outcomes")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


class TestAuthRequired:
    async def test_outcome_endpoints_require_auth(self, client: AsyncClient) -> None:
        client.app.dependency_overrides.clear()

        endpoints = [
            ("POST", "/applications/bbbbbbbbbbbbbbbbbbbbbbbb/outcome"),
            ("GET", "/applications/outcomes"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json={"outcome_status": "applied"})
            assert response.status_code in (401, 403), f"{method} {url} returned {response.status_code}"
