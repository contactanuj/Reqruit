"""
VariablePayBenchmark — pre-aggregated variable pay disbursement rates by company.

Stores historical payout percentages for variable pay components, either
company-specific (crowdsourced) or industry-average (seeded defaults).
"""

from datetime import datetime, timezone

from beanie import Indexed
from pydantic import Field

from src.db.base_document import TimestampedDocument


class VariablePayBenchmark(TimestampedDocument):
    """Variable pay payout benchmark data per company or industry."""

    company_name: Indexed(str)  # type: ignore[valid-type]
    industry: str = ""
    avg_payout_pct: float  # 0-100, e.g. 85.0 means 85% of stated variable is paid
    data_points_count: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    source: str = "industry_average"  # crowdsourced, glassdoor, industry_average

    class Settings:
        name = "variable_pay_benchmarks"
        indexes = [
            [("company_name", 1)],
        ]
