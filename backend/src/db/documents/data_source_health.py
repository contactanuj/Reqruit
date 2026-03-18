"""
DataSourceHealth document — tracks availability and performance of external data sources.

Each external integration (job boards, Gmail API, calendar API, etc.) has a
DataSourceHealth record. The health check Celery task updates these periodically.
Circuit breaker opens after 3 consecutive failures (NFR-6.22).
"""

from datetime import datetime

from pydantic import Field
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class DataSourceHealth(TimestampedDocument):
    """
    Health status for an external data source.

    Fields:
        source_name: Unique identifier (e.g. "indeed_api", "naukri_scraper").
        status: Current health — "healthy", "degraded", or "down".
        last_check_at: When the last health check ran.
        last_success_at: When the last successful check occurred.
        consecutive_failures: Count of sequential failed checks.
        avg_response_ms: Rolling average response time.
        error_rate_24h: Error rate over the last 24 hours (0.0-1.0).
        disabled: Admin manual disable flag.
        last_error: Most recent error message for diagnostics.
    """

    source_name: str
    status: str = Field(default="healthy")
    last_check_at: datetime | None = None
    last_success_at: datetime | None = None
    consecutive_failures: int = 0
    avg_response_ms: float = 0.0
    error_rate_24h: float = 0.0
    disabled: bool = False
    last_error: str = ""

    class Settings:
        name = "data_source_health"
        indexes = [
            IndexModel(
                [("source_name", ASCENDING)],
                unique=True,
            ),
        ]
