"""
Repository for IntegrationConnection documents with token encryption boundary.

This repository is the sole layer that encrypts/decrypts OAuth tokens. The document
model stores raw encrypted bytes; this repository converts plaintext to encrypted
bytes on write and back on explicit decrypt. Raw token values are never logged.
"""

from datetime import UTC, datetime, timedelta

import structlog
from beanie import PydanticObjectId

from src.core.token_encryptor import TokenEncryptor
from src.db.documents.integration_connection import (
    IntegrationConnection,
    IntegrationProvider,
    IntegrationStatus,
)
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class IntegrationConnectionRepository(BaseRepository[IntegrationConnection]):
    """CRUD operations for IntegrationConnection with encrypt/decrypt at the boundary."""

    def __init__(self, encryptor: TokenEncryptor) -> None:
        super().__init__(IntegrationConnection)
        self._encryptor = encryptor

    async def create_connection(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
        oauth_token: str,
        refresh_token: str,
        token_expires_at: datetime,
        scopes: list[str],
    ) -> IntegrationConnection:
        """Create a new integration connection, encrypting tokens before storage."""
        logger.info(
            "integration_connection_creating",
            user_id=str(user_id),
            provider=provider.value,
            oauth_token="[ENCRYPTED]",
            refresh_token="[ENCRYPTED]",
        )
        doc = IntegrationConnection(
            user_id=user_id,
            provider=provider,
            oauth_token_encrypted=self._encryptor.encrypt(oauth_token),
            refresh_token_encrypted=self._encryptor.encrypt(refresh_token),
            token_expires_at=token_expires_at,
            scopes=scopes,
            connected_at=datetime.now(UTC),
            status=IntegrationStatus.CONNECTED,
        )
        return await self.create(doc)

    async def get_by_user_provider(
        self,
        user_id: PydanticObjectId,
        provider: IntegrationProvider,
    ) -> IntegrationConnection | None:
        """Fetch a connection by its unique (user_id, provider) compound key."""
        return await self.find_one(
            {"user_id": user_id, "provider": provider.value}
        )

    async def get_all_by_user(
        self, user_id: PydanticObjectId
    ) -> list[IntegrationConnection]:
        """Return all integration connections for a user."""
        return await self.find_many(filters={"user_id": user_id})

    async def get_connections_needing_refresh(
        self, buffer_minutes: int = 15
    ) -> list[IntegrationConnection]:
        """Return connected integrations whose tokens expire within the buffer window."""
        cutoff = datetime.now(UTC) + timedelta(minutes=buffer_minutes)
        return await self.find_many(
            filters={
                "status": IntegrationStatus.CONNECTED.value,
                "token_expires_at": {"$lt": cutoff},
            }
        )

    async def update_tokens(
        self,
        connection_id: PydanticObjectId,
        oauth_token: str,
        refresh_token: str,
        token_expires_at: datetime,
    ) -> IntegrationConnection | None:
        """Re-encrypt and store new OAuth tokens after a refresh."""
        logger.info(
            "integration_connection_tokens_updating",
            connection_id=str(connection_id),
            oauth_token="[ENCRYPTED]",
            refresh_token="[ENCRYPTED]",
        )
        return await self.update(
            connection_id,
            {
                "oauth_token_encrypted": self._encryptor.encrypt(oauth_token),
                "refresh_token_encrypted": self._encryptor.encrypt(refresh_token),
                "token_expires_at": token_expires_at,
                "status": IntegrationStatus.CONNECTED.value,
            },
        )

    async def update_sync_cursor(
        self,
        connection_id: PydanticObjectId,
        cursor: str,
        last_synced_at: datetime,
    ) -> IntegrationConnection | None:
        """Persist the provider-specific sync cursor and last sync timestamp."""
        return await self.update(
            connection_id,
            {"sync_cursor": cursor, "last_synced_at": last_synced_at},
        )

    async def disconnect(
        self,
        connection_id: PydanticObjectId,
        purge_tokens: bool = True,
    ) -> IntegrationConnection | None:
        """Disconnect an integration, optionally purging encrypted tokens."""
        logger.info(
            "integration_connection_disconnecting",
            connection_id=str(connection_id),
            purge_tokens=purge_tokens,
        )
        update_data: dict = {"status": IntegrationStatus.DISCONNECTED.value}
        if purge_tokens:
            update_data["oauth_token_encrypted"] = b""
            update_data["refresh_token_encrypted"] = b""
        return await self.update(connection_id, update_data)

    def decrypt_tokens(
        self, connection: IntegrationConnection
    ) -> tuple[str, str]:
        """Decrypt both tokens from an IntegrationConnection. Use only at point of API call."""
        logger.debug(
            "integration_connection_decrypting_tokens",
            connection_id=str(connection.id),
            oauth_token="[ENCRYPTED]",
            refresh_token="[ENCRYPTED]",
        )
        oauth_token = self._encryptor.decrypt(connection.oauth_token_encrypted)
        refresh_token = self._encryptor.decrypt(connection.refresh_token_encrypted)
        return oauth_token, refresh_token
