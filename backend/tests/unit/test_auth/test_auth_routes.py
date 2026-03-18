"""
Unit tests for /auth routes.

All external dependencies (UserRepository, RefreshTokenRepository, DB) are
replaced with mocks via FastAPI's dependency_overrides. No real database or
network calls are made.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import (
    get_current_user,
    get_refresh_token_repository,
    get_user_repository,
)
from src.api.main import create_app
from src.core.security import create_access_token, create_refresh_token, hash_password

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    user_id: str = "507f1f77bcf86cd799439011",
    email: str = "test@example.com",
    password: str = "secret123",
    is_active: bool = True,
):
    """Build a mock User object that mimics a Beanie document."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.hashed_password = hash_password(password)
    user.is_active = is_active
    return user


def _mock_user_repo(user=None, email_exists: bool = False):
    """Build a mock UserRepository."""
    repo = AsyncMock()
    repo.email_exists.return_value = email_exists
    repo.get_by_email.return_value = user
    repo.create_user.return_value = user
    repo.get_by_id.return_value = user
    return repo


def _mock_refresh_repo(revoke_by_jti_result: bool = True):
    """Build a mock RefreshTokenRepository."""
    repo = AsyncMock()
    repo.revoke_by_jti.return_value = revoke_by_jti_result
    repo.revoke_family.return_value = 0
    repo.create_token.return_value = MagicMock()
    return repo


@pytest.fixture
async def auth_client():
    """
    HTTP test client with all external dependencies mocked.

    Yields the client and the app so individual tests can swap mocks via
    dependency_overrides without recreating the app.
    """
    from unittest.mock import patch

    with (
        patch("src.api.main.connect_mongodb", new_callable=AsyncMock),
        patch("src.api.main.connect_weaviate", new_callable=AsyncMock),
        patch("src.api.main.close_mongodb"),
        patch("src.api.main.close_weaviate", new_callable=AsyncMock),
        patch("src.api.main.init_embeddings"),
        patch("src.api.main.close_embeddings"),
        patch("src.api.main.init_model_manager"),
        patch("src.api.main.close_model_manager"),
        patch("src.api.main.init_checkpointer"),
        patch("src.api.main.close_checkpointer"),
    ):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, app


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_returns_201_and_tokens(self, auth_client, test_settings):
        ac, app = auth_client
        user = _make_user()
        mock_refresh_repo = _mock_refresh_repo()
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            user=user, email_exists=False
        )
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            response = await ac.post(
                "/auth/register",
                json={"email": "new@example.com", "password": "pass1234"},
            )
            assert response.status_code == 201
            body = response.json()
            assert "access_token" in body
            assert "refresh_token" in body
            assert body["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()

    async def test_register_stores_refresh_token_in_db(self, auth_client, test_settings):
        """AC: Register endpoint stores refresh token in MongoDB."""
        ac, app = auth_client
        user = _make_user()
        mock_refresh_repo = _mock_refresh_repo()
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            user=user, email_exists=False
        )
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            await ac.post(
                "/auth/register",
                json={"email": "new@example.com", "password": "pass1234"},
            )
            mock_refresh_repo.create_token.assert_called_once()
            call_kwargs = mock_refresh_repo.create_token.call_args[1]
            assert call_kwargs["user_id"] == user.id
            assert isinstance(call_kwargs["jti"], str)
            assert isinstance(call_kwargs["family_id"], str)
            assert isinstance(call_kwargs["expires_at"], datetime)
        finally:
            app.dependency_overrides.clear()

    async def test_register_409_if_email_taken(self, auth_client):
        ac, app = auth_client
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            email_exists=True
        )
        try:
            response = await ac.post(
                "/auth/register",
                json={"email": "taken@example.com", "password": "pass1234"},
            )
            assert response.status_code == 409
            assert response.json()["error_code"] == "CONFLICT"
        finally:
            app.dependency_overrides.clear()

    async def test_register_422_invalid_email(self, auth_client):
        ac, app = auth_client
        response = await ac.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "pass1234"},
        )
        assert response.status_code == 422

    async def test_register_422_missing_fields(self, auth_client):
        ac, app = auth_client
        response = await ac.post("/auth/register", json={"email": "a@b.com"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_returns_200_and_tokens(self, auth_client, test_settings):
        ac, app = auth_client
        user = _make_user(password="correct_pass")
        mock_refresh_repo = _mock_refresh_repo()
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            response = await ac.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "correct_pass"},
            )
            assert response.status_code == 200
            body = response.json()
            assert "access_token" in body
            assert "refresh_token" in body
        finally:
            app.dependency_overrides.clear()

    async def test_login_stores_refresh_token_in_db(self, auth_client, test_settings):
        """AC: Login endpoint stores refresh token in MongoDB."""
        ac, app = auth_client
        user = _make_user(password="correct_pass")
        mock_refresh_repo = _mock_refresh_repo()
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            await ac.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "correct_pass"},
            )
            mock_refresh_repo.create_token.assert_called_once()
            call_kwargs = mock_refresh_repo.create_token.call_args[1]
            assert call_kwargs["user_id"] == user.id
            assert isinstance(call_kwargs["jti"], str)
            assert isinstance(call_kwargs["family_id"], str)
        finally:
            app.dependency_overrides.clear()

    async def test_login_401_wrong_password(self, auth_client):
        ac, app = auth_client
        user = _make_user(password="correct_pass")
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        try:
            response = await ac.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "wrong_pass"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_login_401_unknown_email(self, auth_client):
        ac, app = auth_client
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=None)
        try:
            response = await ac.post(
                "/auth/login",
                json={"email": "nobody@example.com", "password": "pass"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_login_401_inactive_account(self, auth_client):
        ac, app = auth_client
        user = _make_user(password="correct_pass", is_active=False)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        try:
            response = await ac.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "correct_pass"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_login_error_message_is_generic(self, auth_client):
        """Verify the error message does not distinguish wrong email vs wrong password."""
        ac, app = auth_client
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=None)
        try:
            response = await ac.post(
                "/auth/login",
                json={"email": "nobody@example.com", "password": "pass"},
            )
            assert "Invalid email or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    async def test_refresh_returns_new_token_pair(self, auth_client, test_settings):
        """AC #1: Valid rotation returns new access + refresh tokens."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id)
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=True)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, _, _ = create_refresh_token(user_id)
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert response.status_code == 200
            body = response.json()
            assert "access_token" in body
            assert "refresh_token" in body
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_revokes_old_token(self, auth_client, test_settings):
        """AC #1: Old token JTI is revoked via CAS."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id)
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=True)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, jti, _, _ = create_refresh_token(user_id)
            await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            mock_refresh_repo.revoke_by_jti.assert_called_once_with(jti)
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_stores_new_token_with_same_family(self, auth_client, test_settings):
        """AC #1: New token is stored in DB with same family_id."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id)
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=True)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, family_id, _ = create_refresh_token(user_id)
            await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            mock_refresh_repo.create_token.assert_called_once()
            call_kwargs = mock_refresh_repo.create_token.call_args[1]
            assert call_kwargs["family_id"] == family_id
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_401_reused_token(self, auth_client, test_settings):
        """AC #2: Reusing already-rotated token returns 401."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        # revoke_by_jti returns False = token already revoked
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=False)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            user=_make_user(user_id=user_id)
        )
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, _, _ = create_refresh_token(user_id)
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert response.status_code == 401
            assert response.json()["error_code"] == "AUTH_TOKEN_INVALID"
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_reuse_triggers_family_revocation(self, auth_client, test_settings):
        """AC #2: Reuse triggers family revocation."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=False)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            user=_make_user(user_id=user_id)
        )
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, family_id, _ = create_refresh_token(user_id)
            await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            mock_refresh_repo.revoke_family.assert_called_once_with(family_id)
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_concurrent_race_second_gets_401(self, auth_client, test_settings):
        """AC #3: Concurrent requests - only one succeeds (mock CAS behavior)."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id)

        # First call succeeds, second fails (simulates CAS race)
        mock_refresh_repo = _mock_refresh_repo()
        mock_refresh_repo.revoke_by_jti = AsyncMock(side_effect=[True, False])
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, _, _ = create_refresh_token(user_id)

            # First request succeeds
            r1 = await ac.post("/auth/refresh", json={"refresh_token": refresh_token})
            assert r1.status_code == 200

            # Second request with same token fails
            r2 = await ac.post("/auth/refresh", json={"refresh_token": refresh_token})
            assert r2.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_401_old_format_no_jti(self, auth_client, test_settings):
        """Backward compat: old-format token without JTI returns 401."""
        ac, app = auth_client
        settings = test_settings
        # Create a token the old way - no jti, no family_id
        now = datetime.now(UTC)
        payload = {
            "sub": "507f1f77bcf86cd799439011",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=7),
        }
        old_token = pyjwt.encode(
            payload,
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm,
        )
        try:
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": old_token},
            )
            assert response.status_code == 401
            assert response.json()["error_code"] == "AUTH_TOKEN_INVALID"
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_401_with_access_token(self, auth_client, test_settings):
        """Using an access token where a refresh token is expected should fail."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        access_token = create_access_token(user_id)
        try:
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": access_token},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_401_invalid_token(self, auth_client):
        ac, app = auth_client
        response = await ac.post(
            "/auth/refresh",
            json={"refresh_token": "not.a.real.token"},
        )
        assert response.status_code == 401

    async def test_refresh_401_inactive_user(self, auth_client, test_settings):
        """Deactivated user is rejected during refresh even with valid token."""
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        inactive_user = _make_user(user_id=user_id, is_active=False)
        mock_refresh_repo = _mock_refresh_repo(revoke_by_jti_result=True)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(
            user=inactive_user
        )
        app.dependency_overrides[get_refresh_token_repository] = lambda: mock_refresh_repo
        try:
            refresh_token, _, _, _ = create_refresh_token(user_id)
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    async def test_refresh_401_expired_token(self, auth_client, test_settings):
        """Expired refresh token returns 401 (JWT expiry check before DB lookup)."""
        ac, app = auth_client
        settings = test_settings
        now = datetime.now(UTC)
        payload = {
            "sub": "507f1f77bcf86cd799439011",
            "type": "refresh",
            "jti": "deadbeef",
            "family_id": "somefamily",
            "iat": now - timedelta(days=8),
            "exp": now - timedelta(days=1),
        }
        expired_token = pyjwt.encode(
            payload,
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm,
        )
        try:
            response = await ac.post(
                "/auth/refresh",
                json={"refresh_token": expired_token},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


class TestGetMe:
    async def test_me_returns_user_info(self, auth_client, test_settings):
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id, email="me@example.com")
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            access_token = create_access_token(user_id)
            response = await ac.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["email"] == "me@example.com"
            assert body["id"] == user_id
            assert body["is_active"] is True
        finally:
            app.dependency_overrides.clear()

    async def test_me_401_without_token(self, auth_client):
        ac, app = auth_client
        response = await ac.get("/auth/me")
        assert response.status_code == 401  # HTTPBearer returns 401 when no credentials

    async def test_me_401_with_refresh_token(self, auth_client, test_settings):
        ac, app = auth_client
        user_id = "507f1f77bcf86cd799439011"
        user = _make_user(user_id=user_id)
        app.dependency_overrides[get_user_repository] = lambda: _mock_user_repo(user=user)
        try:
            refresh_token, _, _, _ = create_refresh_token(user_id)
            response = await ac.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {refresh_token}"},
            )
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()
