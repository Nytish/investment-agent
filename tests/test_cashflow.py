"""Tests for cashflow.py — APEX 2.0"""
import sys
from pathlib import Path
from decimal import Decimal
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from cashflow import (
    calculate_income, calculate_expenses, calculate_surplus,
    calculate_savings, months_of_expenses_covered, _d
)

# ── Fixtures ──────────────────────────────────────────────────────────────

PROFILE = {
    "income": {
        "net_monthly": 4315.34,
        "kindergeld_monthly": 250.00,
        "verification_status": "UNVERIFIED — from user input, not payslip",
        "employment_risk": "Moderate",
    },
    "expenses": {
        "rent": 1200.00,
        "groceries": 400.00,
        "electricity_internet": 100.00,
        "miscellaneous": 200.00,
        "unlisted_expense_warning": True,
        "verification_status": "UNVERIFIED — listed expenses only",
    },
    "savings": {
        "revolut_instant": {"balance": 20416.91, "rate_pct": 2.00},
        "scalable_capital_tagesgeld": {"balance": 15223.00, "rate_pct": 2.50},
        "verification_status": "UNVERIFIED",
    },
}

# ── Income tests ──────────────────────────────────────────────────────────

def test_income_net_monthly():
    result = calculate_income(PROFILE)
    assert result.net_monthly == _d("4315.34")

def test_income_total_includes_kindergeld():
    result = calculate_income(PROFILE)
    assert result.total_monthly == _d("4565.34")

def test_income_verification_status_unverified():
    result = calculate_income(PROFILE)
    assert "UNVERIFIED" in result.verification_status

# ── Expense tests ─────────────────────────────────────────────────────────

def test_listed_expenses_sum_to_1900():
    result = calculate_expenses(PROFILE)
    assert result.total_listed == _d("1900.00"), (
        f"Expected €1900.00, got €{result.total_listed}"
    )

def test_expense_components():
    result = calculate_expenses(PROFILE)
    assert result.rent == _d("1200.00")
    assert result.groceries == _d("400.00")
    assert result.electricity_internet == _d("100.00")
    assert result.miscellaneous == _d("200.00")

def test_unlisted_warning_is_set():
    result = calculate_expenses(PROFILE)
    assert result.unlisted_warning is True

# ── Surplus tests ─────────────────────────────────────────────────────────

def test_gross_surplus_arithmetic():
    income = calculate_income(PROFILE)
    expenses = calculate_expenses(PROFILE)
    surplus = calculate_surplus(income, expenses)
    # 4315.34 - 1900.00 = 2415.34
    assert surplus.gross_surplus == _d("2415.34"), (
        f"Expected €2415.34, got €{surplus.gross_surplus}"
    )

def test_surplus_always_unverified_when_expenses_unverified():
    income = calculate_income(PROFILE)
    expenses = calculate_expenses(PROFILE)
    surplus = calculate_surplus(income, expenses)
    assert surplus.verification_status == "UNVERIFIED"

def test_surplus_has_unlisted_warning():
    income = calculate_income(PROFILE)
    expenses = calculate_expenses(PROFILE)
    surplus = calculate_surplus(income, expenses)
    assert len(surplus.warnings) > 0
    assert any("UNVERIFIED" in w.upper() or "unlisted" in w.lower() for w in surplus.warnings)

# ── Savings tests ─────────────────────────────────────────────────────────

def test_savings_total():
    result = calculate_savings(PROFILE)
    assert result.total_savings == _d("35639.91")

def test_savings_verification_unverified():
    result = calculate_savings(PROFILE)
    assert "UNVERIFIED" in result.verification_status

# ── Coverage tests ────────────────────────────────────────────────────────

def test_expense_coverage_months():
    savings = calculate_savings(PROFILE)
    expenses = calculate_expenses(PROFILE)
    coverage = months_of_expenses_covered(savings.total_savings, expenses.total_listed)
    # 35639.91 / 1900 = ~18.8 months
    assert coverage >= Decimal("18.0")
    assert coverage <= Decimal("19.5")

def test_coverage_raises_on_zero_expenses():
    with pytest.raises(ValueError):
        months_of_expenses_covered(Decimal("10000"), Decimal("0"))

# ── Edge cases ────────────────────────────────────────────────────────────

def test_decimal_precision_no_float_drift():
    """Decimal arithmetic must not produce floating-point drift."""
    income = calculate_income(PROFILE)
    expenses = calculate_expenses(PROFILE)
    surplus = calculate_surplus(income, expenses)
    # Convert to string and check exact representation
    assert str(surplus.gross_surplus) == "2415.34"
