"""
Base migration class — defines the contract for all schema migrations.

Each migration operates on a single collection and transitions documents
from one schema_version to the next. Migrations are idempotent — running
them twice on an already-migrated document has no effect because the
version filter prevents re-processing.
"""

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class Migration(ABC):
    """
    Abstract base for schema migrations.

    Subclasses must define:
        - collection_name: MongoDB collection to migrate
        - from_version: schema_version to match (documents to migrate)
        - to_version: schema_version to set after migration
        - up(): forward migration logic
        - down(): rollback migration logic
    """

    collection_name: str
    from_version: int
    to_version: int
    description: str = ""

    @abstractmethod
    async def up(self, document: dict) -> dict:
        """
        Transform a document from from_version to to_version.

        Args:
            document: The raw MongoDB document dict.

        Returns:
            The transformed document dict with updated fields.
        """

    @abstractmethod
    async def down(self, document: dict) -> dict:
        """
        Reverse the migration (rollback).

        Args:
            document: The raw MongoDB document dict at to_version.

        Returns:
            The document dict restored to from_version.
        """

    def __repr__(self) -> str:
        return (
            f"<Migration {self.collection_name} "
            f"v{self.from_version}→v{self.to_version}: {self.description}>"
        )
