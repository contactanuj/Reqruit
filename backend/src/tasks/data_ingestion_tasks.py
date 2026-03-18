"""
Celery tasks for external data ingestion — company verification and market signals.

refresh_external_data: runs every 6 hours via Beat, refreshes company
verification data and market signals from external sources.
"""

import structlog

from src.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="tasks.batch.refresh_external_data",
    max_retries=1,
    default_retry_delay=60,
)
def refresh_external_data():
    """
    Periodic task: refresh external data for company verification and market signals.

    For each company in the database:
    1. Query healthy external sources for verification data
    2. Update company research with verification results
    3. Record data freshness per source
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_refresh_all())
    finally:
        loop.close()


async def _refresh_all():
    """Run full external data refresh cycle."""
    from src.repositories.company_repository import CompanyRepository
    from src.repositories.data_source_health_repository import (
        DataSourceHealthRepository,
    )
    from src.services.external_data_service import ExternalDataService

    service = ExternalDataService(
        company_repo=CompanyRepository(),
        health_repo=DataSourceHealthRepository(),
    )

    company_result = await service.refresh_all_companies()
    signal_result = await service.ingest_market_signals()

    combined = {
        "companies_refreshed": company_result["refreshed"],
        "company_errors": company_result["errors"],
        "signals_created": signal_result["signals_created"],
    }

    logger.info("external_data_refresh_completed", **combined)
    return combined
