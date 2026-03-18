"""Tests for CompanyVerificationClient — domain, employee, registration checks."""

from src.integrations.base_client import BaseExternalClient
from src.integrations.verification_client import CompanyVerificationClient


class TestCompanyVerificationClient:
    def test_inherits_base_client(self):
        client = CompanyVerificationClient()
        assert isinstance(client, BaseExternalClient)

    async def test_verify_domain_with_domain(self):
        client = CompanyVerificationClient()
        result = await client.verify_domain("acme.com")
        assert result["verified"] is True
        assert result["domain"] == "acme.com"

    async def test_verify_domain_without_domain(self):
        client = CompanyVerificationClient()
        result = await client.verify_domain("")
        assert result["verified"] is False
        assert result["reason"] == "no_domain"

    async def test_estimate_employee_count(self):
        client = CompanyVerificationClient()
        result = await client.estimate_employee_count("Acme Corp")
        assert result["company"] == "Acme Corp"
        assert result["source"] == "employee_estimate"

    async def test_check_registration(self):
        client = CompanyVerificationClient()
        result = await client.check_registration("Acme Corp", "US")
        assert result["company"] == "Acme Corp"
        assert result["country"] == "US"

    async def test_health_check(self):
        client = CompanyVerificationClient()
        assert await client.health_check() is True
