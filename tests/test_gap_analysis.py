"""
tests/test_gap_analysis.py — APEX 2.0
Unit tests for core/gap_analysis.py
All assertions use Decimal arithmetic — no float comparisons.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from gap_analysis import (
    HomeGapResult,
    FireGapResult,
    calculate_home_gap,
    calculate_fire_gap,
    _fv_after_n_months,
    _monthly_needed_for_target,
    _monthly_rate_from_annual,
)


# ─────────────────────────────────────────────────────────────────────────────
# HomeGap tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateHomeGap:
    def test_already_covered(self):
        """Savings exceed down payment — shortfall is zero, covered immediately."""
        result = calculate_home_gap(
            target_price=Decimal("300000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("70000"),
            monthly_surplus=Decimal("2000"),
        )
        assert result.already_covered is True
        assert result.shortfall == Decimal("0")
        assert result.months_to_target == 0
        assert result.years_to_target == Decimal("0")
        assert result.down_payment_required == Decimal("60000.00")

    def test_exactly_covered(self):
        """Savings equal down payment exactly — covered."""
        result = calculate_home_gap(
            target_price=Decimal("400000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("80000"),
            monthly_surplus=Decimal("1500"),
        )
        assert result.already_covered is True
        assert result.shortfall == Decimal("0")
        assert result.months_to_target == 0

    def test_shortfall_calculation(self):
        """Ingolstadt scenario: €360K property, 20% down, €50K savings."""
        result = calculate_home_gap(
            target_price=Decimal("360000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("50000"),
            monthly_surplus=Decimal("2515"),
        )
        assert result.down_payment_required == Decimal("72000.00")
        assert result.shortfall == Decimal("22000.00")
        assert result.already_covered is False
        # ceil(22000 / 2515) = ceil(8.748…) = 9
        assert result.months_to_target == 9

    def test_months_to_target_arithmetic(self):
        """Verify months_to_target uses ceiling division correctly."""
        result = calculate_home_gap(
            target_price=Decimal("100000"),
            down_pct=Decimal("0.10"),
            current_savings=Decimal("0"),
            monthly_surplus=Decimal("1000"),
        )
        assert result.down_payment_required == Decimal("10000.00")
        assert result.shortfall == Decimal("10000.00")
        assert result.months_to_target == 10  # 10000 / 1000 = exactly 10

    def test_months_to_target_ceiling(self):
        """Non-divisible shortfall → ceiling (not floor)."""
        result = calculate_home_gap(
            target_price=Decimal("200000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("35001"),
            monthly_surplus=Decimal("1000"),
        )
        # shortfall = 40000 - 35001 = 4999; ceil(4999/1000) = 5
        assert result.shortfall == Decimal("4999.00")
        assert result.months_to_target == 5

    def test_zero_surplus_not_covered_returns_minus_one(self):
        """Zero monthly surplus and gap exists → impossible, returns -1."""
        result = calculate_home_gap(
            target_price=Decimal("500000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("0"),
            monthly_surplus=Decimal("0"),
        )
        assert result.months_to_target == -1
        assert result.already_covered is False

    def test_30_percent_down(self):
        """30% down payment calculation."""
        result = calculate_home_gap(
            target_price=Decimal("360000"),
            down_pct=Decimal("0.30"),
            current_savings=Decimal("50000"),
            monthly_surplus=Decimal("2000"),
        )
        assert result.down_payment_required == Decimal("108000.00")
        assert result.shortfall == Decimal("58000.00")
        assert result.months_to_target == 29  # ceil(58000/2000) = 29

    def test_all_fields_are_decimal(self):
        """Result fields must be Decimal, not float."""
        result = calculate_home_gap(
            target_price=Decimal("300000"),
            down_pct=Decimal("0.20"),
            current_savings=Decimal("10000"),
            monthly_surplus=Decimal("1500"),
        )
        assert isinstance(result.target_price, Decimal)
        assert isinstance(result.down_payment_required, Decimal)
        assert isinstance(result.shortfall, Decimal)
        assert isinstance(result.monthly_surplus, Decimal)
        assert isinstance(result.years_to_target, Decimal)


# ─────────────────────────────────────────────────────────────────────────────
# FireGap tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateFireGap:
    def test_fire_target_is_25x_expenses(self):
        """FIRE target = 25 × annual expenses (4% rule)."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("21600"),
            current_invested=Decimal("0"),
            monthly_investment=Decimal("500"),
            current_age=36,
            target_fire_age=47,
        )
        assert result.fire_target == Decimal("540000.00")

    def test_fire_with_zero_invested(self):
        """No existing portfolio — FIRE driven entirely by monthly contributions."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("21600"),
            current_invested=Decimal("0"),
            monthly_investment=Decimal("500"),
            current_age=36,
            target_fire_age=47,
        )
        assert result.fire_target == Decimal("540000.00")
        assert result.current_invested == Decimal("0")
        # At €500/month, 7% return, €540K target → takes more than 11 years (47-36)
        assert result.fire_age > 47
        assert result.years_to_fire > Decimal("11")

    def test_fire_with_existing_portfolio(self):
        """Large existing portfolio dramatically reduces time to FIRE."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("20000"),
            current_invested=Decimal("400000"),  # already 80% of FIRE target
            monthly_investment=Decimal("1000"),
            current_age=36,
            target_fire_age=47,
        )
        assert result.fire_target == Decimal("500000.00")
        # Should reach FIRE in a few years, not decades
        assert result.years_to_fire < Decimal("10")
        assert result.fire_age < 50

    def test_monthly_needed_to_hit_target_age(self):
        """monthly_needed_to_hit_age: reasonable value when target is achievable."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("21600"),
            current_invested=Decimal("0"),
            monthly_investment=Decimal("0"),   # no current investment
            current_age=36,
            target_fire_age=53,               # give 17 years
        )
        # With 17 years (204 months) at 7%, some monthly amount must be computable
        assert result.monthly_needed_to_hit_age > 0
        assert result.monthly_needed_to_hit_age < 10_000  # sanity check

    def test_already_on_fire_target(self):
        """Portfolio already equals or exceeds FIRE target → immediate."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("20000"),
            current_invested=Decimal("600000"),  # > 25×20000 = 500000
            monthly_investment=Decimal("0"),
            current_age=36,
            target_fire_age=47,
        )
        assert result.fire_target == Decimal("500000.00")
        # Should reach FIRE in month 1
        assert result.years_to_fire <= Decimal("0.1")

    def test_unreachable_in_50_years_returns_999(self):
        """Zero investment and huge target → unreachable sentinel values."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("100000"),  # FIRE target €2.5M
            current_invested=Decimal("0"),
            monthly_investment=Decimal("0"),
            current_age=36,
            target_fire_age=47,
        )
        assert result.fire_age == 999
        assert result.years_to_fire == Decimal("999")

    def test_fire_result_fields_are_decimal(self):
        """Monetary fields in FireGapResult must be Decimal."""
        result = calculate_fire_gap(
            annual_expenses=Decimal("18000"),
            current_invested=Decimal("10000"),
            monthly_investment=Decimal("800"),
            current_age=36,
            target_fire_age=50,
        )
        assert isinstance(result.fire_target, Decimal)
        assert isinstance(result.current_invested, Decimal)
        assert isinstance(result.monthly_investment, Decimal)
        assert isinstance(result.assumed_annual_return, Decimal)
        assert isinstance(result.years_to_fire, Decimal)

    def test_nitish_realistic_scenario(self):
        """
        Nitish's actual scenario: €21,600/year, €0 invested, €500/month.
        FIRE target €540K. At 7% real return from age 36.
        Expected: reaches FIRE around age 53–55.
        """
        result = calculate_fire_gap(
            annual_expenses=Decimal("21600"),
            current_invested=Decimal("0"),
            monthly_investment=Decimal("500"),
            current_age=36,
            target_fire_age=47,
        )
        # €500/month at 7% to reach €540K takes ~29 years → age ~65
        # (verified: FV = 500 * ((1.07^(1/12))^348 - 1) / (1.07^(1/12) - 1) ≈ €540K)
        assert result.fire_age >= 60
        assert result.fire_age <= 70
        # monthly_needed_to_hit_age=47 is very high (only 11 years for €540K)
        assert result.monthly_needed_to_hit_age > 2000


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_fv_zero_rate(self):
        """With 0% return, FV = PV + PMT*n."""
        fv = _fv_after_n_months(Decimal("1000"), Decimal("100"), Decimal("0"), 12)
        assert fv == Decimal("2200")

    def test_fv_positive_rate(self):
        """FV with positive rate must exceed simple sum."""
        fv = _fv_after_n_months(Decimal("1000"), Decimal("100"), Decimal("0.005"), 12)
        simple = Decimal("1000") + Decimal("100") * Decimal("12")
        assert fv > simple

    def test_monthly_needed_zero_if_already_covered(self):
        """If existing investment already reaches target, monthly_needed = 0."""
        monthly_rate = _monthly_rate_from_annual(Decimal("0.07"))
        needed = _monthly_needed_for_target(
            fire_target=Decimal("100000"),
            current_invested=Decimal("200000"),  # already double the target
            monthly_rate=monthly_rate,
            target_months=120,
        )
        assert needed == 0

    def test_monthly_rate_from_annual_positive(self):
        """Monthly rate for 7% annual is positive and roughly 7%/12."""
        rate = _monthly_rate_from_annual(Decimal("0.07"))
        # Approximate: 0.07/12 ≈ 0.00583; compound gives ~0.00565
        assert Decimal("0.005") < rate < Decimal("0.007")
