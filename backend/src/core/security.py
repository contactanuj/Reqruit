"""
JWT token creation/decoding and password hashing.

Design decisions
----------------
Why PyJWT (not python-jose):
    python-jose has been unmaintained since 2021. FastAPI's official docs
    switched to recommending PyJWT[crypto] in 2025. PyJWT is actively
    maintained and supports HS256, RS256, and ES256 natively.

Why separate access and refresh tokens:
    Access tokens are short-lived (15 min) to limit exposure if stolen.
    Refresh tokens are long-lived (7 days) and used only to rotate the pair.
    The `type` claim in the payload prevents a refresh token from being used
    as an access token and vice versa.

Why bcrypt directly (not passlib):
    passlib 1.7.4 is incompatible with bcrypt 4+. bcrypt dropped the
    __about__ module that passlib relies on for version detection. Since we
    only need bcrypt (no need for passlib's multi-algorithm support), we use
    bcrypt directly. Hashes are stored as UTF-8 strings (decoded from bytes).

Token payload format:
    {
        "sub": "<user_id as string>",   # subject (standard JWT claim)
        "type": "access" | "refresh",   # prevents token type confusion
        "exp": <unix timestamp>,         # expiry (standard JWT claim)
        "iat": <unix timestamp>,         # issued at (standard JWT claim)
    }
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt

from src.core.config import get_settings
from src.core.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns a UTF-8 string."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


def create_access_token(user_id: str) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: String representation of the user's MongoDB ObjectId.

    Returns:
        Signed JWT string (HS256).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )


def create_refresh_token(
    user_id: str,
    family_id: str | None = None,
    *,
    now: datetime | None = None,
) -> tuple[str, str, str, datetime]:
    """
    Create a long-lived JWT refresh token with JTI and family tracking.

    Args:
        user_id: String representation of the user's MongoDB ObjectId.
        family_id: Reuse existing family on rotation; None creates a new
            family (login/register).
        now: Optional timestamp for token creation. When provided, the same
            value drives both the JWT ``exp`` claim and the returned
            ``expires_at``, eliminating clock drift between the JWT and the
            server-side token record.

    Returns:
        Tuple of (token_string, jti, family_id, expires_at).
    """
    jti = uuid4().hex
    if family_id is None:
        family_id = uuid4().hex

    settings = get_settings()
    if now is None:
        now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.auth.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "family_id": family_id,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )
    return token, jti, family_id, expires_at


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Validates the signature and expiry. Does NOT check the `type` claim —
    that is the caller's responsibility to prevent type confusion attacks.

    Args:
        token: JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        AuthenticationError: If the token is expired or has an invalid signature.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError("Invalid token") from e
