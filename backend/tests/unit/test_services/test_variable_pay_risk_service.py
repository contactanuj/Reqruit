"""
Tests for VariablePayRiskService — deterministic variable pay risk analysis.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.variable_pay_risk_service import VariablePayRiskService


def _make_benchmark(avg_payout_pct: float = 85.0, data_points: int = 100):
    b = MagicMock()
    b.avg_payout_pct = avg_payout_pct
    b.data_points_count = data_points
    b.last_updated = datetime(2025, 6, 1, tzinfo=timezone.utc)
    return b


def _make_repo(company_benchmark=None, industry_benchmark=None):
    repo = MagicMock()
    repo.get_by_company = AsyncMock(return_value=company_benchmark)
    repo.get_industry_average = AsyncMock(return_value=industry_benchmark)
    return repo


class TestStatedVariableAmount:

    async def test_stated_amount_computed_correctly(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark())
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme Corp", 15.0, 2000000)
        assert result.stated_variable_amount == 300000.0  # 2M * 15%

    async def test_zero_variable_pct(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark())
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme Corp", 0.0, 2000000)
        assert result.stated_variable_amount == 0.0
        assert result.expected_actual_amount == 0.0


class TestDataSourceLookup:

    async def test_company_specific_benchmark(self) -> None:
        bench = _make_benchmark(avg_payout_pct=92.0, data_points=80)
        repo = _make_repo(company_benchmark=bench)
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme Corp", 15.0, 2000000)
        assert result.data_source == "company_specific"
        assert result.estimated_actual_payout_pct == 92.0
        assert result.data_points_count == 80

    async def test_industry_average_fallback(self) -> None:
        industry = _make_benchmark(avg_payout_pct=78.0, data_points=500)
        repo = _make_repo(company_benchmark=None, industry_benchmark=industry)
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Unknown Corp", 15.0, 2000000)
        assert result.data_source == "industry_average"
        assert result.estimated_actual_payout_pct == 78.0

    async def test_hardcoded_fallback_when_no_benchmark(self) -> None:
        repo = _make_repo(company_benchmark=None, industry_benchmark=None)
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Unknown Corp", 15.0, 2000000)
        assert result.data_source == "industry_average"
        assert result.estimated_actual_payout_pct == 80.0  # hardcoded default
        assert result.data_points_count is None
        assert result.last_updated is None


class TestRiskLevel:

    async def test_low_risk_above_90(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=95.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.risk_level == "LOW"

    async def test_medium_risk_at_90(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=90.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.risk_level == "MEDIUM"

    async def test_medium_risk_at_70(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=70.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.risk_level == "MEDIUM"

    async def test_high_risk_below_70(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=60.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.risk_level == "HIGH"


class TestHighVariableWarning:

    async def test_warning_when_above_30_pct(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=95.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 35.0, 2000000)
        assert result.high_variable_warning is not None
        assert "at-risk pay" in result.high_variable_warning

    async def test_risk_forced_to_high_when_above_30_pct(self) -> None:
        # Even with 95% payout (LOW risk), variable_pay_pct > 30 forces HIGH
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=95.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 35.0, 2000000)
        assert result.risk_level == "HIGH"

    async def test_no_warning_at_exactly_30_pct(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=95.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 30.0, 2000000)
        assert result.high_variable_warning is None
        assert result.risk_level == "LOW"

    async def test_fully_variable_100_pct(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=95.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 100.0, 2000000)
        assert result.risk_level == "HIGH"
        assert result.high_variable_warning is not None
        assert result.stated_variable_amount == 2000000.0


class TestConfidence:

    async def test_high_confidence_company_many_points(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(data_points=100))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.confidence == "high"

    async def test_medium_confidence_company_few_points(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(data_points=20))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        assert result.confidence == "medium"

    async def test_low_confidence_industry_average(self) -> None:
        repo = _make_repo(company_benchmark=None, industry_benchmark=None)
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Unknown", 15.0, 2000000)
        assert result.confidence == "low"


class TestExpectedAmount:

    async def test_expected_amount_computation(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=80.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 20.0, 1000000)
        # stated = 200000, expected = 200000 * 0.8 = 160000
        assert result.expected_actual_amount == 160000.0

    async def test_net_post_tax_value_formula(self) -> None:
        repo = _make_repo(company_benchmark=_make_benchmark(avg_payout_pct=85.0))
        svc = VariablePayRiskService(repo)
        result = await svc.analyze("Acme", 15.0, 2000000)
        # stated = 300000, expected = 300000 * 0.85 = 255000
        assert result.stated_variable_amount == 300000.0
        assert result.expected_actual_amount == pytest.approx(255000.0)
