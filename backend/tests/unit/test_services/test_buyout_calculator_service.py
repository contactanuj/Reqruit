"""
Tests for BuyoutCalculatorService — deterministic notice period buyout calculator.
"""

import time
from datetime import date, timedelta

import pytest

from src.services.buyout_calculator_service import BuyoutCalculatorService


class TestRemainingDays:

    def test_remaining_days_computed(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        assert result.remaining_days == 60

    def test_full_notice_remaining(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=0,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        assert result.remaining_days == 90

    def test_zero_remaining(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=90,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        assert result.remaining_days == 0
        assert result.buyout_cost == 0.0


class TestBuyoutCost:

    def test_buyout_cost_formula(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=60000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        # daily_rate = 60000/30 = 2000, buyout_cost = 2000 * 60 = 120000
        assert result.daily_rate == 2000.0
        assert result.buyout_cost == 120000.0

    def test_daily_rate(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        assert result.daily_rate == pytest.approx(50000 / 30, rel=1e-2)


class TestBuyoutRequired:

    def test_buyout_required_when_joining_before_natural_end(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 1, 1)
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),  # before natural end (Mar 2)
            notice_start_date=start,
        )
        assert result.buyout_required is True
        assert result.gap_days is not None
        assert result.gap_days > 0

    def test_buyout_not_required_when_joining_after_natural_end(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 1, 1)
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 6, 1),  # well after natural end
            notice_start_date=start,
        )
        assert result.buyout_required is False
        assert result.gap_days is None

    def test_gap_days_computed(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 1, 1)
        # remaining = 60, natural_end = Jan 1 + 60 = Mar 2
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            notice_start_date=start,
        )
        # gap = Mar 2 - Feb 1 = 29 days
        expected_natural_end = date(2026, 3, 2)
        expected_gap = (expected_natural_end - date(2026, 2, 1)).days
        assert result.gap_days == expected_gap


class TestJoiningBonusOffset:

    def test_full_coverage(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 1, 1)
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            joining_bonus=200000,  # more than buyout cost
            notice_start_date=start,
        )
        assert result.net_out_of_pocket is not None
        assert result.net_out_of_pocket <= 0
        assert result.recommendation == "Your joining bonus fully covers the buyout cost"

    def test_partial_coverage(self) -> None:
        svc = BuyoutCalculatorService()
        # buyout_cost = (50000/30) * 60 = 100000
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            joining_bonus=75000,  # 75k of 100k → net = 25k < 50% of 100k
            notice_start_date=date(2026, 1, 1),
        )
        assert result.net_out_of_pocket is not None
        assert result.net_out_of_pocket > 0
        assert "partial buyout" in result.recommendation.lower()

    def test_minimal_coverage(self) -> None:
        svc = BuyoutCalculatorService()
        # buyout_cost = (50000/30) * 60 = 100000
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            joining_bonus=10000,  # 10k of 100k → net = 90k >= 50% of 100k
            notice_start_date=date(2026, 1, 1),
        )
        assert result.net_out_of_pocket is not None
        assert result.net_out_of_pocket >= result.buyout_cost * 0.5
        assert "strongly recommend" in result.recommendation.lower()

    def test_no_joining_bonus(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            notice_start_date=date(2026, 1, 1),
        )
        assert result.net_out_of_pocket is None
        assert result.recommendation is None


class TestNoticeStartDate:

    def test_with_explicit_start_date(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 3, 1)
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=60,
            served_days=0,
            offer_joining_date=date(2026, 5, 1),
            notice_start_date=start,
        )
        # natural_end = Mar 1 + 60 = Apr 30
        assert result.natural_end_date == date(2026, 4, 30)
        assert result.buyout_required is False

    def test_without_start_date_uses_today(self) -> None:
        svc = BuyoutCalculatorService()
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=60,
            served_days=0,
            offer_joining_date=date.today() + timedelta(days=200),
        )
        expected = date.today() + timedelta(days=60)
        assert result.natural_end_date == expected


class TestTypicalIndianScenario:

    def test_90_day_notice_30_served_join_in_30(self) -> None:
        svc = BuyoutCalculatorService()
        start = date(2026, 1, 1)
        result = svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 1, 31),
            notice_start_date=start,
        )
        assert result.remaining_days == 60
        assert result.buyout_required is True
        # daily_rate = 50000/30 ≈ 1666.67, buyout = 1666.67 * 60 = 100000
        assert result.buyout_cost == pytest.approx(100000.0, rel=1e-2)


class TestPerformance:

    def test_completes_in_under_200ms(self) -> None:
        svc = BuyoutCalculatorService()
        start_time = time.perf_counter()
        svc.calculate(
            monthly_basic=50000,
            contractual_notice_days=90,
            served_days=30,
            offer_joining_date=date(2026, 2, 1),
            joining_bonus=75000,
            notice_start_date=date(2026, 1, 1),
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        assert elapsed_ms < 200
