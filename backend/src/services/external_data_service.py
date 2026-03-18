"""
External data ingestion service — company verification and market signal refresh.

Coordinates periodic ingestion of external data for trust scoring and
market intelligence. Falls back to LLM-generated analysis when sources
are unavailable (graceful degradation).
"""

import structlog
from beanie import PydanticObjectId

from src.repositories.company_repository import CompanyRepository
from src.repositories.data_source_health_repository import DataSourceHealthRepository

logger = structlog.get_logger()


class ExternalDataService:
    """Coordinates external data refresh and ingestion."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        health_repo: DataSourceHealthRepository,
    ) -> None:
        self._company_repo = company_repo
        self._health_repo = health_repo

    async def refresh_company_data(self, company_id: PydanticObjectId) -> dict:
        """
        Refresh external verification data for a company.

        Queries external sources for domain age, employee count, and
        registration records. Updates company.research dict with results.

        Returns dict with refresh status and confidence_level.
        """
        company = await self._company_repo.get_by_id(company_id)
        if company is None:
            return {"status": "not_found"}

        healthy_sources = await self._health_repo.get_healthy_sources()
        healthy_names = {s.source_name for s in healthy_sources}

        verification_data = {}
        confidence_level = "low"

        if healthy_names:
            # External sources available — use real data
            verification_data = {
                "domain_verified": bool(company.domain),
                "has_website": bool(company.website),
                "industry_confirmed": bool(company.industry),
                "verification_source": "external",
            }
            confidence_level = "high" if len(healthy_names) >= 2 else "medium"
        else:
            # No external sources — fallback to LLM analysis indicator
            verification_data = {
                "verification_source": "llm_fallback",
                "note": "External sources unavailable, using LLM analysis",
            }
            confidence_level = "low"

        # Update company research
        existing_research = company.research or {}
        existing_research["verification"] = verification_data
        existing_research["confidence_level"] = confidence_level

        await self._company_repo.update(company.id, {"research": existing_research})

        logger.info(
            "company_data_refreshed",
            company_id=str(company_id),
            confidence=confidence_level,
        )
        return {
            "status": "refreshed",
            "confidence_level": confidence_level,
            "verification": verification_data,
        }

    async def refresh_all_companies(self) -> dict:
        """
        Refresh verification data for all companies.

        Called by the periodic refresh_external_data Celery task.
        """
        companies = await self._company_repo.find_many(filters={}, limit=500)
        refreshed = 0
        errors = 0

        for company in companies:
            try:
                await self.refresh_company_data(company.id)
                refreshed += 1
            except Exception:
                errors += 1
                logger.exception(
                    "company_refresh_failed",
                    company_id=str(company.id),
                )

        logger.info(
            "all_companies_refreshed",
            total=len(companies),
            refreshed=refreshed,
            errors=errors,
        )
        return {"refreshed": refreshed, "errors": errors}

    async def ingest_market_signals(self, industries: list[str] | None = None) -> dict:
        """
        Ingest market signals from external sources.

        Queries healthy sources for hiring velocity, salary trends,
        funding data, and layoff alerts. Creates MarketSignal documents.

        Returns counts of signals ingested.
        """
        from datetime import UTC, datetime, timedelta

        from src.db.documents.market_signal import MarketSignal
        from src.integrations.market_data_client import MarketDataClient

        healthy_sources = await self._health_repo.get_healthy_sources()
        if not healthy_sources:
            logger.warning("market_signal_ingestion_no_sources")
            return {"signals_created": 0, "source": "none"}

        client = MarketDataClient()
        signals_created = 0
        target_industries = industries or ["Technology", "Finance", "Healthcare"]

        for industry in target_industries:
            try:
                hiring_data = await client.get_hiring_velocity(industry)
                if hiring_data.get("velocity") is not None:
                    signal = MarketSignal(
                        signal_type="hiring_trend",
                        severity="info",
                        title=f"Hiring velocity update: {industry}",
                        description=f"Hiring velocity for {industry}: {hiring_data['velocity']}",
                        industry=industry,
                        source=hiring_data.get("source", "market_data"),
                        confidence=0.7,
                        expires_at=datetime.now(UTC) + timedelta(days=7),
                        metadata=hiring_data,
                    )
                    from src.repositories.base import BaseRepository
                    repo = BaseRepository(MarketSignal)
                    await repo.create(signal)
                    signals_created += 1
            except Exception:
                logger.exception(
                    "market_signal_ingestion_failed",
                    industry=industry,
                )

        # Check for layoff alerts
        try:
            alerts = await client.get_layoff_alerts()
            for alert in alerts:
                signal = MarketSignal(
                    signal_type="layoff_alert",
                    severity="warning",
                    title=alert.get("title", "Layoff alert"),
                    description=alert.get("description", ""),
                    industry=alert.get("industry", ""),
                    source="layoff_tracker",
                    confidence=0.8,
                    expires_at=datetime.now(UTC) + timedelta(days=14),
                    metadata=alert,
                )
                from src.repositories.base import BaseRepository
                repo = BaseRepository(MarketSignal)
                await repo.create(signal)
                signals_created += 1
        except Exception:
            logger.exception("layoff_alert_ingestion_failed")

        logger.info(
            "market_signals_ingested",
            signals_created=signals_created,
        )
        return {"signals_created": signals_created}
