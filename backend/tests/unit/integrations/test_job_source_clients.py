"""Tests for job source clients — Indeed, Naukri, LinkedIn RSS."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.base_client import ExternalAPIError
from src.integrations.job_source_clients import (
    JOB_SOURCE_REGISTRY,
    IndeedClient,
    LinkedInRSSClient,
    NaukriClient,
)


class TestIndeedClient:
    def test_inherits_base_client(self):
        client = IndeedClient(api_key="test_key")
        assert hasattr(client, "_check_circuit")
        assert hasattr(client, "_record_success")

    async def test_search_jobs_parses_response(self):
        client = IndeedClient(api_key="key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Software Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://indeed.com/j/123",
                    "salary": "$100k-$150k",
                    "snippet": "Great opportunity",
                    "date": "2026-03-15",
                }
            ]
        }
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            results = await client.search_jobs("python developer", location="US")
        assert len(results) == 1
        assert results[0].source == "indeed"
        assert results[0].title == "Software Engineer"
        assert results[0].company == "Acme"

    async def test_health_check_success(self):
        client = IndeedClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            assert await client.health_check() is True

    async def test_health_check_failure(self):
        client = IndeedClient()
        with patch.object(client, "_request", new_callable=AsyncMock, side_effect=Exception("down")):
            assert await client.health_check() is False


class TestNaukriClient:
    def test_inherits_base_client(self):
        client = NaukriClient()
        assert hasattr(client, "_check_circuit")

    async def test_search_jobs_parses_response(self):
        client = NaukriClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "jobDetails": [
                {
                    "title": "Backend Developer",
                    "companyName": "TechCo",
                    "jdURL": "https://naukri.com/j/456",
                    "salary": "15-25 LPA",
                    "placeholders": [{"label": "Bangalore"}],
                    "jobDescription": "Looking for backend dev with Python experience.",
                    "createdDate": "2026-03-14",
                }
            ]
        }
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            results = await client.search_jobs("python", location="Bangalore")
        assert len(results) == 1
        assert results[0].source == "naukri"
        assert results[0].company == "TechCo"
        assert results[0].location == "Bangalore"

    async def test_health_check_failure(self):
        client = NaukriClient()
        with patch.object(client, "_request", new_callable=AsyncMock, side_effect=Exception("err")):
            assert await client.health_check() is False


class TestLinkedInRSSClient:
    def test_inherits_base_client(self):
        client = LinkedInRSSClient()
        assert hasattr(client, "_check_circuit")

    async def test_search_jobs_returns_empty(self):
        client = LinkedInRSSClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            results = await client.search_jobs("engineer")
        # LinkedIn RSS returns HTML that needs parsing — stub returns empty
        assert results == []

    async def test_health_check_success(self):
        client = LinkedInRSSClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
            assert await client.health_check() is True


class TestJobSourceRegistry:
    def test_registry_has_three_sources(self):
        assert len(JOB_SOURCE_REGISTRY) == 3

    def test_registry_contains_expected_sources(self):
        assert "indeed_api" in JOB_SOURCE_REGISTRY
        assert "naukri_scraper" in JOB_SOURCE_REGISTRY
        assert "linkedin_rss" in JOB_SOURCE_REGISTRY

    def test_registry_values_are_client_classes(self):
        assert JOB_SOURCE_REGISTRY["indeed_api"] is IndeedClient
        assert JOB_SOURCE_REGISTRY["naukri_scraper"] is NaukriClient
        assert JOB_SOURCE_REGISTRY["linkedin_rss"] is LinkedInRSSClient


class TestCircuitBreakerIntegration:
    async def test_circuit_opens_after_failures(self):
        client = IndeedClient(failure_threshold=2, recovery_timeout=60.0)
        # Simulate 2 failures
        client._record_failure()
        client._record_failure()
        assert client._circuit_open is True

    def test_circuit_blocks_when_open(self):
        client = IndeedClient(failure_threshold=2, recovery_timeout=9999.0)
        client._record_failure()
        client._record_failure()
        import pytest
        with pytest.raises(ExternalAPIError) as exc_info:
            client._check_circuit()
        assert exc_info.value.status_code == 503

    def test_success_resets_circuit(self):
        client = IndeedClient(failure_threshold=2)
        client._record_failure()
        client._record_failure()
        assert client._circuit_open is True
        client._record_success()
        assert client._circuit_open is False
        assert client._failure_count == 0
