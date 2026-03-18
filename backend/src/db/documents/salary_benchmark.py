"""
Salary benchmark document — market compensation data for percentile positioning.

Stores aggregated salary data by role, region, and experience level.
Data sources include AmbitionBox, Glassdoor, levels.fyi. For India,
benchmarks use CTC (not base salary). For US, total comp.
"""

from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class SalaryBenchmark(TimestampedDocument):
    """
    Market salary benchmark for a role + region combination.

    Fields:
        role: Normalized job title (e.g., "Software Engineer", "SDE-2").
        role_family: Broader category for fallback matching (e.g., "Software Engineer").
        region_code: ISO country/region code (e.g., "IN", "US").
        city: Optional city for more specific benchmarks.
        experience_years_min: Minimum experience for this band.
        experience_years_max: Maximum experience for this band.
        p25: 25th percentile compensation.
        p50: 50th percentile (median).
        p75: 75th percentile.
        p90: 90th percentile.
        sample_size: Number of data points backing this benchmark.
        currency_code: ISO currency code (INR, USD).
        source: Data source (e.g., "AmbitionBox", "levels.fyi").
        data_freshness: Description of data recency (e.g., "2025-Q4").
    """

    role: str
    role_family: str = ""
    region_code: str
    city: str = ""
    experience_years_min: int = 0
    experience_years_max: int = 99
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    p90: float = 0.0
    sample_size: int = 0
    currency_code: str = "INR"
    source: str = ""
    data_freshness: str = ""

    class Settings:
        name = "salary_benchmarks"
        indexes = [
            IndexModel(
                [("role", ASCENDING), ("region_code", ASCENDING)],
                name="role_region_idx",
            ),
            IndexModel(
                [("role_family", ASCENDING), ("region_code", ASCENDING)],
                name="family_region_idx",
            ),
        ]
