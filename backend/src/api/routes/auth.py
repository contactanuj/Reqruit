"""
Authentication routes: register, login, refresh, and current user.

Design decisions
----------------
Why inline Pydantic schemas (not a separate schemas/ directory):
    This is the only module that uses these schemas — they are auth-specific
    request/response shapes. A shared schemas/ directory adds indirection
    without benefit at this scale.

Why return tokens on register (not just 201):
    Registering and immediately logging in is the expected UX. Making the
    client do a second round-trip after register adds latency for no gain.

Why generic "Invalid email or password" on login failure:
    Returning "email not found" vs "wrong password" would let attackers
    enumerate registered accounts. A single generic message prevents that.

Why rotate both tokens on refresh (not just issue a new access token):
    Refresh token rotation limits the window where a stolen refresh token
    can be used. Once the legitimate client uses it, the old token is
    invalidated server-side via atomic CAS revocation.

Endpoints
---------
    POST /auth/register   Create account, return token pair
    POST /auth/login      Verify credentials, return token pair
    POST /auth/refresh    Rotate token pair using a valid refresh token
    GET  /auth/me         Return current user from access token
"""

import structlog
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from src.api.dependencies import (
    get_current_user,
    get_refresh_token_repository,
    get_user_repository,
)
from src.core.exceptions import AuthenticationError, ConflictError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.db.documents.user import User
from src.repositories.refresh_token_repository import RefreshTokenRepository
from src.repositories.user_repository import UserRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenResponse:
    """
    Create a new account and return a JWT token pair.

    Raises 409 if the email is already registered.
    """
    if await user_repo.email_exists(body.email):
        raise ConflictError("Email already registered")

    hashed = hash_password(body.password)
    user = await user_repo.create_user(email=body.email, hashed_password=hashed)
    user_id = str(user.id)

    refresh_token, jti, family_id, expires_at = create_refresh_token(user_id)
    await refresh_token_repo.create_token(
        user_id=user.id, jti=jti, family_id=family_id, expires_at=expires_at
    )

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenResponse:
    """
    Verify credentials and return a JWT token pair.

    Uses a generic error message to prevent account enumeration.
    """
    user = await user_repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    user_id = str(user.id)
    refresh_token, jti, family_id, expires_at = create_refresh_token(user_id)
    await refresh_token_repo.create_token(
        user_id=user.id, jti=jti, family_id=family_id, expires_at=expires_at
    )

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenResponse:
    """
    Rotate the token pair using a valid refresh token.

    Server-side rotation with token family tracking:
    1. Decode JWT and extract JTI + family_id
    2. Atomically revoke the old token (CAS)
    3. If already revoked -> reuse attack -> revoke entire family -> 401
    4. Issue new pair with same family_id
    """
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type")

    jti = payload.get("jti")
    family_id = payload.get("family_id")

    # Backward compat: old tokens without JTI are rejected
    if not jti or not family_id:
        logger.warning("refresh_token_old_format", sub=payload.get("sub"))
        raise AuthenticationError(
            "Invalid token format", error_code="AUTH_TOKEN_INVALID"
        )

    # Atomic CAS: try to revoke this specific token
    was_revoked = await refresh_token_repo.revoke_by_jti(jti)
    if not was_revoked:
        # Token was already revoked = REUSE ATTACK
        await refresh_token_repo.revoke_family(family_id)
        logger.warning(
            "refresh_token_reuse_detected", jti=jti, family_id=family_id
        )
        raise AuthenticationError(
            "Token has been revoked", error_code="AUTH_TOKEN_INVALID"
        )

    # Validate user
    user_id_obj = PydanticObjectId(payload["sub"])
    user = await user_repo.get_by_id(user_id_obj)
    if not user or not user.is_active:
        raise AuthenticationError("User not found or deactivated")

    # Issue new pair with same family
    user_id = str(user.id)
    new_token, new_jti, _, expires_at = create_refresh_token(
        user_id, family_id=family_id
    )
    await refresh_token_repo.create_token(
        user_id=user.id, jti=new_jti, family_id=family_id, expires_at=expires_at
    )

    logger.info("refresh_token_rotated", user_id=user_id, family_id=family_id)

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=new_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current authenticated user's profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
    )
