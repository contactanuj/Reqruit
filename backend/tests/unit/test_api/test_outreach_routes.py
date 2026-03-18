"""
Unit tests for outreach message routes.

Coverage:
- POST /outreach/generate — generate outreach draft (201, 404 application, 404 contact)
- GET /outreach — list messages (with and without application_id filter)
- GET /outreach/{message_id} — get single message
- PATCH /outreach/{message_id} — edit draft
- POST /outreach/{message_id}/send — mark as sent
- DELETE /outreach/{message_id} — delete message
- Auth required (401)
"""

from unittest.mock import AsyncMock, MagicMock, patch

from beanie import PydanticObjectId
from httpx import AsyncClient

from src.api.dependencies import (
    get_application_repository,
    get_contact_repository,
    get_current_user,
    get_job_repository,
    get_outreach_message_repository,
)
from src.db.documents.application import Application
from src.db.documents.contact import Contact
from src.db.documents.enums import MessageType
from src.db.documents.job import Job
from src.db.documents.outreach_message import OutreachMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
APP_ID = "bbbbbbbbbbbbbbbbbbbbbbbb"
CONTACT_ID = "cccccccccccccccccccccccc"
JOB_ID = "dddddddddddddddddddddddd"
MSG_ID = "eeeeeeeeeeeeeeeeeeeeeeee"


def _make_user(user_id: str = USER_ID):
    user = MagicMock()
    user.id = PydanticObjectId(user_id)
    user.email = "test@example.com"
    return user


def _make_application(app_id: str = APP_ID, job_id: str = JOB_ID):
    app = MagicMock(spec=Application)
    app.id = PydanticObjectId(app_id)
    app.user_id = PydanticObjectId(USER_ID)
    app.job_id = PydanticObjectId(job_id)
    return app


def _make_contact(contact_id: str = CONTACT_ID):
    contact = MagicMock(spec=Contact)
    contact.id = PydanticObjectId(contact_id)
    contact.name = "Jane Smith"
    contact.role = "Engineering Manager"
    return contact


def _make_job(job_id: str = JOB_ID):
    job = MagicMock(spec=Job)
    job.id = PydanticObjectId(job_id)
    job.title = "Software Engineer"
    job.company_name = "Acme Corp"
    job.description = "Build scalable systems."
    return job


def _make_message(msg_id: str = MSG_ID, is_sent: bool = False):
    msg = MagicMock(spec=OutreachMessage)
    msg.id = PydanticObjectId(msg_id)
    msg.user_id = PydanticObjectId(USER_ID)
    msg.application_id = PydanticObjectId(APP_ID)
    msg.contact_id = PydanticObjectId(CONTACT_ID)
    msg.message_type = MessageType.GENERIC
    msg.content = "Hi Jane, I noticed your team..."
    msg.is_sent = is_sent
    msg.sent_at = None
    msg.created_at = None
    msg.updated_at = None
    return msg


def _setup(app, mock_outreach_repo=None, mock_app_repo=None,
           mock_contact_repo=None, mock_job_repo=None):
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    if mock_outreach_repo:
        app.dependency_overrides[get_outreach_message_repository] = lambda: mock_outreach_repo
    if mock_app_repo:
        app.dependency_overrides[get_application_repository] = lambda: mock_app_repo
    if mock_contact_repo:
        app.dependency_overrides[get_contact_repository] = lambda: mock_contact_repo
    if mock_job_repo:
        app.dependency_overrides[get_job_repository] = lambda: mock_job_repo


# ---------------------------------------------------------------------------
# Tests: POST /outreach/generate
# ---------------------------------------------------------------------------


class TestGenerateOutreach:
    async def test_generate_201(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = _make_application()
        mock_contact_repo = AsyncMock()
        mock_contact_repo.get_by_id.return_value = _make_contact()
        mock_job_repo = AsyncMock()
        mock_job_repo.get_by_id.return_value = _make_job()
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.create.return_value = _make_message()
        _setup(app, mock_outreach_repo, mock_app_repo, mock_contact_repo, mock_job_repo)

        with patch(
            "src.agents.outreach.OutreachComposer.__call__",
            new_callable=AsyncMock,
            return_value={"content": "Hi Jane, I noticed your team..."},
        ):
            try:
                resp = await client.post(
                    "/outreach/generate",
                    json={
                        "application_id": APP_ID,
                        "contact_id": CONTACT_ID,
                        "message_type": "generic",
                    },
                )
                assert resp.status_code == 201
                data = resp.json()
                assert data["content"] == "Hi Jane, I noticed your team..."
                assert data["id"] == MSG_ID
            finally:
                app.dependency_overrides.clear()

    async def test_generate_404_application(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = None
        mock_contact_repo = AsyncMock()
        mock_job_repo = AsyncMock()
        mock_outreach_repo = AsyncMock()
        _setup(app, mock_outreach_repo, mock_app_repo, mock_contact_repo, mock_job_repo)

        try:
            resp = await client.post(
                "/outreach/generate",
                json={"application_id": APP_ID, "contact_id": CONTACT_ID},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_generate_404_contact(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_app_repo = AsyncMock()
        mock_app_repo.get_by_user_and_id.return_value = _make_application()
        mock_contact_repo = AsyncMock()
        mock_contact_repo.get_by_id.return_value = None
        mock_job_repo = AsyncMock()
        mock_outreach_repo = AsyncMock()
        _setup(app, mock_outreach_repo, mock_app_repo, mock_contact_repo, mock_job_repo)

        try:
            resp = await client.post(
                "/outreach/generate",
                json={"application_id": APP_ID, "contact_id": CONTACT_ID},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /outreach — list messages
# ---------------------------------------------------------------------------


class TestListOutreachMessages:
    async def test_list_all_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_for_user.return_value = [_make_message()]
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.get("/outreach")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            app.dependency_overrides.clear()

    async def test_list_filtered_by_application(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_for_application.return_value = [_make_message()]
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.get(f"/outreach?application_id={APP_ID}")
            assert resp.status_code == 200
            mock_outreach_repo.get_for_application.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_list_empty(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_for_user.return_value = []
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.get("/outreach")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /outreach/{message_id}
# ---------------------------------------------------------------------------


class TestGetOutreachMessage:
    async def test_get_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = _make_message()
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.get(f"/outreach/{MSG_ID}")
            assert resp.status_code == 200
            assert resp.json()["id"] == MSG_ID
        finally:
            app.dependency_overrides.clear()

    async def test_get_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.get(f"/outreach/{MSG_ID}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: PATCH /outreach/{message_id} — edit draft
# ---------------------------------------------------------------------------


class TestUpdateOutreachMessage:
    async def test_update_content_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        updated_msg = _make_message()
        updated_msg.content = "Updated content"
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = _make_message()
        mock_outreach_repo.update.return_value = updated_msg
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.patch(
                f"/outreach/{MSG_ID}",
                json={"content": "Updated content"},
            )
            assert resp.status_code == 200
            mock_outreach_repo.update.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_update_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.patch(
                f"/outreach/{MSG_ID}",
                json={"content": "Updated"},
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /outreach/{message_id}/send — mark as sent
# ---------------------------------------------------------------------------


class TestMarkAsSent:
    async def test_mark_sent_200(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = _make_message()
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.post(f"/outreach/{MSG_ID}/send")
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_sent"] is True
            assert data["sent_at"] is not None
        finally:
            app.dependency_overrides.clear()

    async def test_mark_sent_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.post(f"/outreach/{MSG_ID}/send")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_mark_sent_422_already_sent(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = _make_message(is_sent=True)
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.post(f"/outreach/{MSG_ID}/send")
            assert resp.status_code == 422
            assert resp.json()["error_code"] == "ALREADY_SENT"
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: DELETE /outreach/{message_id}
# ---------------------------------------------------------------------------


class TestDeleteOutreachMessage:
    async def test_delete_204(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = _make_message()
        mock_outreach_repo.delete.return_value = True
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.delete(f"/outreach/{MSG_ID}")
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()

    async def test_delete_404(self, client: AsyncClient):
        app = client.app  # type: ignore[attr-defined]
        mock_outreach_repo = AsyncMock()
        mock_outreach_repo.get_by_user_and_id.return_value = None
        _setup(app, mock_outreach_repo)

        try:
            resp = await client.delete(f"/outreach/{MSG_ID}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: Auth required
# ---------------------------------------------------------------------------


class TestOutreachAuth:
    async def test_generate_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/outreach/generate",
            json={"application_id": APP_ID, "contact_id": CONTACT_ID},
        )
        assert resp.status_code == 401

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/outreach")
        assert resp.status_code == 401
