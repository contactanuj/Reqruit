"""
Repository for server-side refresh token operations.

Provides atomic compare-and-swap (CAS) revocation for safe token rotation
and family-level revocation for theft detection.
"""

from datetime import datetime

import structlog
from beanie import PydanticObjectId

from src.db.documents.refresh_token import RefreshToken
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Refresh token data access with atomic CAS revocation."""

    def __init__(self) -> None:
        super().__init__(RefreshToken)

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        """Find a refresh token record by its JWT ID."""
        return await self.find_one({"token_jti": jti})

    async def revoke_by_jti(self, jti: str) -> bool:
        """
        Atomically revoke a token by JTI (compare-and-swap).

        Returns True if THIS call revoked it (first writer wins).
        Returns False if already revoked or not found — indicates reuse.
        """
        collection = RefreshToken.get_pymongo_collection()
        result = await collection.find_one_and_update(
            {"token_jti": jti, "is_revoked": False},
            {"$set": {"is_revoked": True}},
        )
        return result is not None

    async def revoke_family(self, family_id: str) -> int:
        """
        Revoke ALL tokens in a family (theft detection response).

        Returns the number of tokens that were newly revoked.
        """
        result = await RefreshToken.find(
            {"family_id": family_id, "is_revoked": False}
        ).update_many({"$set": {"is_revoked": True}})
        count = result.modified_count if result else 0
        if count > 0:
            logger.warning("refresh_token_family_revoked", family_id=family_id, revoked_count=count)
        else:
            logger.info("refresh_token_family_revoke_noop", family_id=family_id)
        return count

    async def create_token(
        self,
        user_id: PydanticObjectId,
        jti: str,
        family_id: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a new refresh token record."""
        token = RefreshToken(
            user_id=user_id,
            token_jti=jti,
            family_id=family_id,
            expires_at=expires_at,
        )
        return await self.create(token)
