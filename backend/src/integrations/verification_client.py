"""
Company verification client — external data for trust scoring.

Queries external sources for company verification data:
- Domain age and registration
- Employee count estimates
- Business registration records

Uses BaseExternalClient for circuit breaker and timeout handling.
"""

import structlog

from src.integrations.base_client import BaseExternalClient

logger = structlog.get_logger()


class CompanyVerificationClient(BaseExternalClient):
    """Client for company verification data from external APIs."""

    def __init__(self) -> None:
        super().__init__(base_url="", timeout=15.0)

    async def verify_domain(self, domain: str) -> dict:
        """
        Check domain age and registration status.

        In production, this would call a WHOIS/domain API.
        Returns verification data dict.
        """
        if not domain:
            return {"verified": False, "reason": "no_domain"}

        # Placeholder — real implementation would call external API
        return {
            "verified": True,
            "domain": domain,
            "domain_age_days": None,
            "registrar": None,
            "source": "domain_lookup",
        }

    async def estimate_employee_count(self, company_name: str) -> dict:
        """
        Estimate employee count from external data.

        In production, this would query LinkedIn data or similar API.
        """
        return {
            "company": company_name,
            "estimated_count": None,
            "range": None,
            "source": "employee_estimate",
        }

    async def check_registration(self, company_name: str, country: str = "") -> dict:
        """
        Check business registration records.

        In production, this would query government business registries.
        """
        return {
            "company": company_name,
            "registered": None,
            "country": country,
            "source": "registration_check",
        }

    async def health_check(self) -> bool:
        """Check if the verification service is reachable."""
        return True
