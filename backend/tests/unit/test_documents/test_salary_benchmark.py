"""Tests for the SalaryBenchmark document model."""

from src.db.documents.salary_benchmark import SalaryBenchmark


class TestSalaryBenchmark:

    def test_collection_name(self) -> None:
        assert SalaryBenchmark.Settings.name == "salary_benchmarks"

    def test_create_with_required_fields(self) -> None:
        bm = SalaryBenchmark(role="SDE-2", region_code="IN")
        assert bm.role == "SDE-2"
        assert bm.region_code == "IN"
        assert bm.role_family == ""
        assert bm.city == ""
        assert bm.p25 == 0.0
        assert bm.p50 == 0.0
        assert bm.p75 == 0.0
        assert bm.p90 == 0.0
        assert bm.sample_size == 0
        assert bm.currency_code == "INR"
        assert bm.source == ""
        assert bm.data_freshness == ""

    def test_create_with_all_fields(self) -> None:
        bm = SalaryBenchmark(
            role="Software Engineer",
            role_family="Software Engineer",
            region_code="IN",
            city="Bangalore",
            experience_years_min=2,
            experience_years_max=5,
            p25=1500000,
            p50=2000000,
            p75=3000000,
            p90=4000000,
            sample_size=150,
            currency_code="INR",
            source="AmbitionBox",
            data_freshness="2025-Q4",
        )
        assert bm.role_family == "Software Engineer"
        assert bm.city == "Bangalore"
        assert bm.experience_years_min == 2
        assert bm.experience_years_max == 5
        assert bm.p25 == 1500000
        assert bm.p90 == 4000000
        assert bm.sample_size == 150
        assert bm.source == "AmbitionBox"

    def test_indexes_defined(self) -> None:
        index_names = [
            idx.document.get("name", "") for idx in SalaryBenchmark.Settings.indexes
        ]
        assert "role_region_idx" in index_names
        assert "family_region_idx" in index_names

    def test_schema_version_default(self) -> None:
        bm = SalaryBenchmark(role="SDE", region_code="US")
        assert bm.schema_version == 1
