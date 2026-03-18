"""Tests for MarketDataClient — hiring velocity, salary, funding, layoffs."""

from src.integrations.base_client import BaseExternalClient
from src.integrations.market_data_client import MarketDataClient


class TestMarketDataClient:
    def test_inherits_base_client(self):
        client = MarketDataClient()
        assert isinstance(client, BaseExternalClient)

    async def test_get_hiring_velocity(self):
        client = MarketDataClient()
        result = await client.get_hiring_velocity("Technology", "US")
        assert result["industry"] == "Technology"
        assert result["region"] == "US"
        assert result["source"] == "hiring_velocity"

    async def test_get_salary_trends(self):
        client = MarketDataClient()
        result = await client.get_salary_trends("Backend Engineer", "US")
        assert result["role"] == "Backend Engineer"
        assert result["source"] == "salary_trends"

    async def test_get_funding_rounds(self):
        client = MarketDataClient()
        result = await client.get_funding_rounds("Acme Corp")
        assert result["company"] == "Acme Corp"
        assert result["recent_rounds"] == []

    async def test_get_layoff_alerts(self):
        client = MarketDataClient()
        result = await client.get_layoff_alerts("Technology")
        assert result == []

    async def test_health_check(self):
        client = MarketDataClient()
        assert await client.health_check() is True
