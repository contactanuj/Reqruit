"""
Salary benchmark repository — lookup market compensation data.
"""

from src.db.documents.salary_benchmark import SalaryBenchmark
from src.repositories.base import BaseRepository


class SalaryBenchmarkRepository(BaseRepository[SalaryBenchmark]):
    """Salary benchmark data access methods."""

    def __init__(self) -> None:
        super().__init__(SalaryBenchmark)

    async def find_by_role_and_region(
        self, role: str, region_code: str, city: str = ""
    ) -> SalaryBenchmark | None:
        """Find benchmark for exact role + region (+ optional city)."""
        query: dict = {"role": role, "region_code": region_code}
        if city:
            query["city"] = city
        return await self.find_one(query)

    async def find_by_family_and_region(
        self, role_family: str, region_code: str
    ) -> SalaryBenchmark | None:
        """Fallback: find benchmark by role family when exact match missing."""
        return await self.find_one(
            {"role_family": role_family, "region_code": region_code}
        )
