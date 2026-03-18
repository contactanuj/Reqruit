"""
Tests for SalaryBenchmarkRepository query methods.

Verifies that repository methods pass correct filters to BaseRepository.
"""

from unittest.mock import AsyncMock

from src.repositories.salary_benchmark_repository import SalaryBenchmarkRepository


def _make_repo():
    repo = SalaryBenchmarkRepository.__new__(SalaryBenchmarkRepository)
    repo.find_one = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    return repo


class TestFindByRoleAndRegion:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.find_by_role_and_region("SDE-2", "IN")
        repo.find_one.assert_called_once_with(
            {"role": "SDE-2", "region_code": "IN"}
        )

    async def test_includes_city_when_provided(self):
        repo = _make_repo()
        await repo.find_by_role_and_region("SDE-2", "IN", city="Bangalore")
        repo.find_one.assert_called_once_with(
            {"role": "SDE-2", "region_code": "IN", "city": "Bangalore"}
        )


class TestFindByFamilyAndRegion:

    async def test_passes_correct_filter(self):
        repo = _make_repo()
        await repo.find_by_family_and_region("Software Engineer", "IN")
        repo.find_one.assert_called_once_with(
            {"role_family": "Software Engineer", "region_code": "IN"}
        )
