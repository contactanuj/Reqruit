"""
VariablePayBenchmark repository — lookups for variable pay disbursement data.

Provides company-specific and industry-average benchmark queries.
"""

import re

from src.db.documents.variable_pay_benchmark import VariablePayBenchmark
from src.repositories.base import BaseRepository


class VariablePayBenchmarkRepository(BaseRepository[VariablePayBenchmark]):
    """Data access methods for variable pay benchmark lookups."""

    def __init__(self) -> None:
        super().__init__(VariablePayBenchmark)

    async def get_by_company(self, company_name: str) -> VariablePayBenchmark | None:
        """Case-insensitive lookup by company name."""
        return await self.find_one(
            {"company_name": re.compile(f"^{re.escape(company_name)}$", re.IGNORECASE)}
        )

    async def get_industry_average(self, industry: str = "") -> VariablePayBenchmark | None:
        """Fetch industry-average benchmark for the given industry."""
        return await self.find_one(
            {"source": "industry_average", "industry": industry}
        )
