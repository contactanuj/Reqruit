"""
Unit tests for src/core/security.py.

All tests are offline — no database, no network. JWT operations and
bcrypt hashing are pure functions that depend only on the settings singleton.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.core.exceptions import AuthenticationError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$")

    def test_different_salts_each_call(self):
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2

    def test_hash_is_not_plaintext(self):
        assert hash_password("secret") != "secret"


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_empty_password_returns_false(self):
        h = hash_password("mypassword")
        assert verify_password("", h) is False


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_string(self, test_settings):
        token = create_access_token("abc123")
        assert isinstance(token, str)

    def test_type_claim_is_access(self, test_settings):
        token = create_access_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        assert payload["type"] == "access"

    def test_sub_claim_is_user_id(self, test_settings):
        token = create_access_token("user_xyz")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        assert payload["sub"] == "user_xyz"

    def test_expires_in_15_minutes(self, test_settings):
        before = datetime.now(UTC)
        token = create_access_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        delta = exp - before
        # Should be close to 15 minutes (allow 5s tolerance)
        assert timedelta(minutes=14, seconds=55) < delta < timedelta(minutes=15, seconds=5)


class TestCreateRefreshToken:
    def test_returns_tuple_of_four_elements(self, test_settings):
        result = create_refresh_token("abc123")
        assert isinstance(result, tuple)
        assert len(result) == 4
        token, jti, family_id, expires_at = result
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert isinstance(family_id, str)
        assert isinstance(expires_at, datetime)

    def test_type_claim_is_refresh(self, test_settings):
        token, _, _, _ = create_refresh_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        assert payload["type"] == "refresh"

    def test_jti_claim_present(self, test_settings):
        token, jti, _, _ = create_refresh_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        assert payload["jti"] == jti

    def test_family_id_claim_present(self, test_settings):
        token, _, family_id, _ = create_refresh_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        assert payload["family_id"] == family_id

    def test_new_family_id_when_none(self, test_settings):
        _, _, family_id1, _ = create_refresh_token("abc123")
        _, _, family_id2, _ = create_refresh_token("abc123")
        assert family_id1 != family_id2

    def test_reuses_family_id_when_provided(self, test_settings):
        _, _, family_id, _ = create_refresh_token("abc123")
        _, _, reused, _ = create_refresh_token("abc123", family_id=family_id)
        assert reused == family_id

    def test_unique_jti_each_call(self, test_settings):
        _, jti1, _, _ = create_refresh_token("abc123")
        _, jti2, _, _ = create_refresh_token("abc123")
        assert jti1 != jti2

    def test_expires_in_7_days(self, test_settings):
        before = datetime.now(UTC)
        token, _, _, _ = create_refresh_token("abc123")
        settings = test_settings
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        delta = exp - before
        assert timedelta(days=6, hours=23, minutes=59) < delta < timedelta(days=7, seconds=5)

    def test_access_and_refresh_tokens_differ(self, test_settings):
        access = create_access_token("abc123")
        refresh, _, _, _ = create_refresh_token("abc123")
        assert access != refresh


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


class TestDecodeToken:
    def test_decodes_valid_access_token(self, test_settings):
        token = create_access_token("user42")
        payload = decode_token(token)
        assert payload["sub"] == "user42"
        assert payload["type"] == "access"

    def test_decodes_valid_refresh_token(self, test_settings):
        token, _, _, _ = create_refresh_token("user42")
        payload = decode_token(token)
        assert payload["sub"] == "user42"
        assert payload["type"] == "refresh"

    def test_raises_on_expired_token(self, test_settings):
        settings = test_settings
        payload = {
            "sub": "user42",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
            "iat": datetime.now(UTC) - timedelta(minutes=16),
        }
        expired_token = jwt.encode(
            payload,
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm,
        )
        with pytest.raises(AuthenticationError, match="expired"):
            decode_token(expired_token)

    def test_raises_on_tampered_signature(self, test_settings):
        token = create_access_token("user42")
        tampered = token[:-4] + "xxxx"
        with pytest.raises(AuthenticationError, match="Invalid token"):
            decode_token(tampered)

    def test_raises_on_garbage_input(self, test_settings):
        with pytest.raises(AuthenticationError):
            decode_token("not.a.token")

    def test_raises_on_wrong_secret(self, test_settings):
        settings = test_settings
        payload = {
            "sub": "user42",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=settings.auth.jwt_algorithm)
        with pytest.raises(AuthenticationError):
            decode_token(token)
