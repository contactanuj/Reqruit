"""
Job source clients — external job board integrations with circuit breaker.

Each client extends BaseExternalClient to get automatic circuit breaker,
timeout handling, and structured logging. Sources are queried independently
so one slow/failed source does not block others (NFR-6.17, NFR-6.20).

Clients:
    IndeedClient — Indeed job search API
    NaukriClient — Naukri job search (scraper-based)
    LinkedInRSSClient — LinkedIn RSS job feed
"""

import time

import structlog
from pydantic import BaseModel

from src.integrations.base_client import BaseExternalClient

logger = structlog.get_logger()


class JobListing(BaseModel):
    """Normalized job listing from any source."""

    source: str
    source_url: str = ""
    title: str
    company: str
    location: str = ""
    salary_range: str = ""
    description_snippet: str = ""
    posted_date: str = ""


class IndeedClient(BaseExternalClient):
    """Indeed job search API client."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.indeed.com",
        **kwargs,
    ) -> None:
        super().__init__(base_url=base_url, **kwargs)
        self._api_key = api_key

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        limit: int = 25,
    ) -> list[JobListing]:
        """Search Indeed for jobs matching query and location."""
        start = time.monotonic()
        try:
            response = await self._request(
                "GET",
                f"{self._base_url}/v2/search",
                params={"q": query, "l": location, "limit": limit},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "indeed_search_completed",
                query=query,
                results=len(response.json().get("results", [])),
                elapsed_ms=round(elapsed_ms, 1),
            )
            return [
                JobListing(
                    source="indeed",
                    source_url=item.get("url", ""),
                    title=item.get("title", ""),
                    company=item.get("company", ""),
                    location=item.get("location", ""),
                    salary_range=item.get("salary", ""),
                    description_snippet=item.get("snippet", ""),
                    posted_date=item.get("date", ""),
                )
                for item in response.json().get("results", [])
            ]
        except Exception:
            logger.exception("indeed_search_failed", query=query)
            raise

    async def health_check(self) -> bool:
        """Check if Indeed API is reachable."""
        try:
            response = await self._request("GET", f"{self._base_url}/v2/health")
            return response.status_code == 200
        except Exception:
            return False


class NaukriClient(BaseExternalClient):
    """Naukri job search client."""

    def __init__(
        self,
        base_url: str = "https://www.naukri.com",
        **kwargs,
    ) -> None:
        super().__init__(base_url=base_url, **kwargs)

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        limit: int = 25,
    ) -> list[JobListing]:
        """Search Naukri for jobs matching query and location."""
        start = time.monotonic()
        try:
            response = await self._request(
                "GET",
                f"{self._base_url}/jobapi/v3/search",
                params={"keyword": query, "location": location, "pageSize": limit},
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "naukri_search_completed",
                query=query,
                results=len(response.json().get("jobDetails", [])),
                elapsed_ms=round(elapsed_ms, 1),
            )
            return [
                JobListing(
                    source="naukri",
                    source_url=item.get("jdURL", ""),
                    title=item.get("title", ""),
                    company=item.get("companyName", ""),
                    location=item.get("placeholders", [{}])[0].get("label", "")
                    if item.get("placeholders")
                    else "",
                    salary_range=item.get("salary", ""),
                    description_snippet=item.get("jobDescription", "")[:200],
                    posted_date=item.get("createdDate", ""),
                )
                for item in response.json().get("jobDetails", [])
            ]
        except Exception:
            logger.exception("naukri_search_failed", query=query)
            raise

    async def health_check(self) -> bool:
        """Check if Naukri is reachable."""
        try:
            response = await self._request("GET", f"{self._base_url}/jobapi/v3/health")
            return response.status_code == 200
        except Exception:
            return False


class LinkedInRSSClient(BaseExternalClient):
    """LinkedIn RSS job feed client."""

    def __init__(
        self,
        base_url: str = "https://www.linkedin.com",
        **kwargs,
    ) -> None:
        super().__init__(base_url=base_url, **kwargs)

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        limit: int = 25,
    ) -> list[JobListing]:
        """Fetch LinkedIn job feed for query."""
        start = time.monotonic()
        try:
            await self._request(
                "GET",
                f"{self._base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params={"keywords": query, "location": location, "start": 0},
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "linkedin_search_completed",
                query=query,
                elapsed_ms=round(elapsed_ms, 1),
            )
            # LinkedIn RSS returns HTML, would need parsing
            # For now, return empty — real implementation would parse response
            return []
        except Exception:
            logger.exception("linkedin_search_failed", query=query)
            raise

    async def health_check(self) -> bool:
        """Check if LinkedIn job feed is reachable."""
        try:
            await self._request(
                "GET",
                f"{self._base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params={"keywords": "test", "start": 0},
            )
            return True
        except Exception:
            return False


# Registry of all job source clients for iteration
JOB_SOURCE_REGISTRY: dict[str, type[BaseExternalClient]] = {
    "indeed_api": IndeedClient,
    "naukri_scraper": NaukriClient,
    "linkedin_rss": LinkedInRSSClient,
}
