"""
Migration runner — discovers and executes migrations in version order.

Applies migrations to all documents in a collection that match the
from_version filter. Updates schema_version after each document is
transformed. Tracks applied migrations in a _migrations collection
for auditability.
"""

from datetime import UTC, datetime
from typing import Any

import structlog

from src.db.migrations.base import Migration

logger = structlog.get_logger()

MIGRATIONS_COLLECTION = "_migrations"


class MigrationRunner:
    """
    Executes schema migrations against a MongoDB database.

    Usage:
        runner = MigrationRunner(db)
        runner.register(MyMigration())
        result = await runner.run()
    """

    def __init__(self, db: Any) -> None:
        self._db = db
        self._migrations: list[Migration] = []

    def register(self, migration: Migration) -> None:
        """Register a migration for execution."""
        self._migrations.append(migration)

    def _sorted_migrations(self) -> list[Migration]:
        """Return migrations sorted by (collection_name, from_version)."""
        return sorted(
            self._migrations,
            key=lambda m: (m.collection_name, m.from_version),
        )

    async def run(self, direction: str = "up") -> dict:
        """
        Execute all registered migrations.

        Args:
            direction: "up" for forward migration, "down" for rollback.

        Returns:
            Summary dict with counts per migration.
        """
        results = []
        migrations = self._sorted_migrations()
        if direction == "down":
            migrations = list(reversed(migrations))

        for migration in migrations:
            if await self._is_applied(migration) and direction == "up":
                logger.info(
                    "migration_skipped",
                    migration=repr(migration),
                    reason="already_applied",
                )
                results.append({
                    "migration": repr(migration),
                    "status": "skipped",
                    "documents_affected": 0,
                })
                continue

            count = await self._apply(migration, direction)
            await self._record(migration, direction, count)
            results.append({
                "migration": repr(migration),
                "status": "applied",
                "documents_affected": count,
            })

        return {"direction": direction, "migrations": results}

    async def _apply(self, migration: Migration, direction: str) -> int:
        """Apply a single migration to all matching documents within a transaction."""
        collection = self._db[migration.collection_name]

        if direction == "up":
            version_filter = {"schema_version": migration.from_version}
            target_version = migration.to_version
        else:
            version_filter = {"schema_version": migration.to_version}
            target_version = migration.from_version

        # Use a transaction to ensure atomicity — partial failures roll back
        try:
            async with await self._db.client.start_session() as session:
                async with session.start_transaction():
                    cursor = collection.find(version_filter, session=session)
                    count = 0

                    async for doc in cursor:
                        if direction == "up":
                            transformed = await migration.up(doc)
                        else:
                            transformed = await migration.down(doc)

                        transformed["schema_version"] = target_version
                        await collection.replace_one(
                            {"_id": doc["_id"]}, transformed, session=session
                        )
                        count += 1
        except Exception:
            logger.exception(
                "migration_transaction_failed",
                migration=repr(migration),
                direction=direction,
            )
            raise

        logger.info(
            "migration_applied",
            migration=repr(migration),
            direction=direction,
            documents_affected=count,
        )
        return count

    async def _is_applied(self, migration: Migration) -> bool:
        """Check if a migration has already been applied."""
        record = await self._db[MIGRATIONS_COLLECTION].find_one({
            "collection_name": migration.collection_name,
            "from_version": migration.from_version,
            "to_version": migration.to_version,
            "direction": "up",
        })
        return record is not None

    async def _record(
        self, migration: Migration, direction: str, count: int
    ) -> None:
        """Record the migration execution in the _migrations collection."""
        if direction == "down":
            # Remove the "up" record on rollback
            await self._db[MIGRATIONS_COLLECTION].delete_one({
                "collection_name": migration.collection_name,
                "from_version": migration.from_version,
                "to_version": migration.to_version,
                "direction": "up",
            })
        else:
            await self._db[MIGRATIONS_COLLECTION].insert_one({
                "collection_name": migration.collection_name,
                "from_version": migration.from_version,
                "to_version": migration.to_version,
                "direction": direction,
                "documents_affected": count,
                "applied_at": datetime.now(UTC),
                "description": migration.description,
            })
