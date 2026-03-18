"""Tests for ExternalDataService — company verification and data refresh."""

from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId

from src.services.external_data_service import ExternalDataService

COMPANY_ID = PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")


def _make_service(company_repo=None, health_repo=None):
    return ExternalDataService(
        company_repo=company_repo or MagicMock(),
        health_repo=health_repo or MagicMock(),
    )


def _make_company(**overrides):
    defaults = {
        "id": COMPANY_ID,
        "name": "Acme Corp",
        "domain": "acme.com",
        "website": "https://acme.com",
        "industry": "Technology",
        "research": {},
    }
    defaults.update(overrides)
    company = MagicMock()
    for k, v in defaults.items():
        setattr(company, k, v)
    return company


class TestRefreshCompanyData:
    async def test_refreshes_with_external_sources(self):
        company = _make_company()
        healthy = [MagicMock(source_name="s1"), MagicMock(source_name="s2")]

        company_repo = MagicMock()
        company_repo.get_by_id = AsyncMock(return_value=company)
        company_repo.update = AsyncMock()

        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(return_value=healthy)

        service = _make_service(company_repo=company_repo, health_repo=health_repo)
        result = await service.refresh_company_data(COMPANY_ID)

        assert result["status"] == "refreshed"
        assert result["confidence_level"] == "high"
        company_repo.update.assert_awaited_once()

    async def test_medium_confidence_with_one_source(self):
        company = _make_company()
        healthy = [MagicMock(source_name="s1")]

        company_repo = MagicMock()
        company_repo.get_by_id = AsyncMock(return_value=company)
        company_repo.update = AsyncMock()

        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(return_value=healthy)

        service = _make_service(company_repo=company_repo, health_repo=health_repo)
        result = await service.refresh_company_data(COMPANY_ID)

        assert result["confidence_level"] == "medium"

    async def test_fallback_when_no_sources(self):
        company = _make_company()

        company_repo = MagicMock()
        company_repo.get_by_id = AsyncMock(return_value=company)
        company_repo.update = AsyncMock()

        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(return_value=[])

        service = _make_service(company_repo=company_repo, health_repo=health_repo)
        result = await service.refresh_company_data(COMPANY_ID)

        assert result["confidence_level"] == "low"
        assert result["verification"]["verification_source"] == "llm_fallback"

    async def test_returns_not_found_for_missing_company(self):
        company_repo = MagicMock()
        company_repo.get_by_id = AsyncMock(return_value=None)

        service = _make_service(company_repo=company_repo)
        result = await service.refresh_company_data(COMPANY_ID)
        assert result["status"] == "not_found"


class TestRefreshAllCompanies:
    async def test_refreshes_all(self):
        c1 = _make_company(id=COMPANY_ID)
        c2 = _make_company(id=PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"), name="Beta Corp")
        healthy = [MagicMock(source_name="s1")]

        company_repo = MagicMock()
        company_repo.find_many = AsyncMock(return_value=[c1, c2])
        company_repo.get_by_id = AsyncMock(side_effect=lambda cid: c1 if cid == c1.id else c2)
        company_repo.update = AsyncMock()

        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(return_value=healthy)

        service = _make_service(company_repo=company_repo, health_repo=health_repo)
        result = await service.refresh_all_companies()

        assert result["refreshed"] == 2
        assert result["errors"] == 0

    async def test_handles_individual_failures(self):
        c1 = _make_company(id=COMPANY_ID)

        company_repo = MagicMock()
        company_repo.find_many = AsyncMock(return_value=[c1])
        company_repo.get_by_id = AsyncMock(side_effect=Exception("db error"))

        health_repo = MagicMock()

        service = _make_service(company_repo=company_repo, health_repo=health_repo)
        result = await service.refresh_all_companies()

        assert result["errors"] == 1
        assert result["refreshed"] == 0

    async def test_empty_companies(self):
        company_repo = MagicMock()
        company_repo.find_many = AsyncMock(return_value=[])

        service = _make_service(company_repo=company_repo)
        result = await service.refresh_all_companies()

        assert result["refreshed"] == 0
        assert result["errors"] == 0


class TestIngestMarketSignals:
    async def test_returns_zero_when_no_sources(self):
        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(return_value=[])

        service = _make_service(health_repo=health_repo)
        result = await service.ingest_market_signals()

        assert result["signals_created"] == 0
        assert result["source"] == "none"

    async def test_ingests_signals_when_sources_available(self):
        health_repo = MagicMock()
        health_repo.get_healthy_sources = AsyncMock(
            return_value=[MagicMock(source_name="market_api")]
        )

        service = _make_service(health_repo=health_repo)
        # Market data client returns None velocity, so no signals created
        result = await service.ingest_market_signals(industries=["Technology"])

        assert result["signals_created"] == 0  # placeholder returns None velocity
