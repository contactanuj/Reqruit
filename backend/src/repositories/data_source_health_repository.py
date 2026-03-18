"""
Repository for DataSourceHealth documents with upsert and status tracking.

Provides health check recording, status queries, and admin overrides
for external data source monitoring.
"""

from datetime import UTC, datetime

import structlog

from src.db.documents.data_source_health import DataSourceHealth
from src.repositories.base import BaseRepository

logger = structlog.get_logger()


class DataSourceHealthRepository(BaseRepository[DataSourceHealth]):
    """CRUD operations for DataSourceHealth with upsert-based health recording."""

    def __init__(self) -> None:
        super().__init__(DataSourceHealth)

    async def record_check(
        self,
        source_name: str,
        success: bool,
        response_ms: float = 0.0,
        error: str = "",
    ) -> DataSourceHealth:
        """
        Record a health check result for a source.

        Creates the record if it doesn't exist (upsert pattern).
        Updates consecutive_failures and status based on the result.
        """
        now = datetime.now(UTC)
        existing = await self.find_one({"source_name": source_name})

        if existing is None:
            health = DataSourceHealth(
                source_name=source_name,
                status="healthy" if success else "degraded",
                last_check_at=now,
                last_success_at=now if success else None,
                consecutive_failures=0 if success else 1,
                avg_response_ms=response_ms,
                last_error=error,
            )
            return await self.create(health)

        updates: dict = {"last_check_at": now}

        if success:
            updates["consecutive_failures"] = 0
            updates["last_success_at"] = now
            updates["last_error"] = ""
            # Transition: down/degraded → healthy on success
            if existing.status != "healthy":
                updates["status"] = "healthy"
                logger.info(
                    "data_source_recovered",
                    source=source_name,
                    previous_status=existing.status,
                )
        else:
            new_failures = existing.consecutive_failures + 1
            updates["consecutive_failures"] = new_failures
            updates["last_error"] = error
            if new_failures >= 3:
                updates["status"] = "down"
                logger.warning(
                    "data_source_down",
                    source=source_name,
                    consecutive_failures=new_failures,
                )
            else:
                updates["status"] = "degraded"

        # Rolling average (simple exponential moving average)
        if response_ms > 0:
            alpha = 0.3
            updates["avg_response_ms"] = (
                alpha * response_ms + (1 - alpha) * existing.avg_response_ms
            )

        return await self.update(existing.id, updates)

    async def get_all_sources(self) -> list[DataSourceHealth]:
        """Return all data source health records."""
        return await self.find_many(filters={}, sort="source_name")

    async def get_healthy_sources(self) -> list[DataSourceHealth]:
        """Return sources that are not down and not disabled."""
        return await self.find_many(
            filters={"status": {"$ne": "down"}, "disabled": False}
        )

    async def set_disabled(self, source_name: str, disabled: bool) -> DataSourceHealth | None:
        """Admin toggle to manually enable/disable a source."""
        existing = await self.find_one({"source_name": source_name})
        if existing is None:
            return None
        return await self.update(existing.id, {"disabled": disabled})
