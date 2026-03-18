"""
RefreshToken document — tracks server-side refresh token state for rotation.

Each refresh token issued by the system gets a record here. Tokens belong to
a "family" that groups all tokens from a single login session. When a rotated
token is reused (indicating theft), the entire family is revoked.

Fields
------
    user_id: Owner of the token.
    token_jti: JWT ID claim — unique identifier for the specific token.
    family_id: Groups tokens from the same login/register session.
    is_revoked: Set to True atomically when the token is consumed or revoked.
    expires_at: Mirrors the JWT exp claim for query purposes.
"""

from datetime import datetime

from beanie import Indexed, PydanticObjectId

from src.db.base_document import TimestampedDocument


class RefreshToken(TimestampedDocument):
    """Server-side record for refresh token rotation and reuse detection."""

    user_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    token_jti: Indexed(str, unique=True)  # type: ignore[valid-type]
    family_id: Indexed(str)  # type: ignore[valid-type]
    is_revoked: bool = False
    expires_at: datetime

    class Settings:
        name = "refresh_tokens"
