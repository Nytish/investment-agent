"""Tests for buckets.py — APEX 2.0
Model: existing €50K = emergency buffer (locked).
       house fund + LT investing = built from future monthly surplus.
"""
import sys
from pathlib import Path
from decimal import Decimal
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from buckets import allocate_buckets, BucketStatus


D = Decimal

TOTAL_SAVINGS    = D("50000.00")    # Scalable Capital — emergency buffer
MONTHLY_EXPENSES = D("1900.00")


# ── Emergency reserve — uses EXISTING savings ──────────────────────────────

def test_emergency_balance_equals_full_savings():
    """The full existing savings are designated as emergency buffer."""
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES)
    assert alloc.emergency.balance == TOTAL_SAVINGS


def test_emergency_funded_when_savings_exceed_target():
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES, emergency_months=6)
    assert alloc.emergency.status == BucketStatus.FUNDED


def test_emergency_underfunded_when_savings_below_target():
    alloc = allocate_buckets(D("5000.00"), MONTHLY_EXPENSES, emergency_months=6)
    assert alloc.emergency.status == BucketStatus.UNDERFUNDED


def test_emergency_target_calculated_correctly():
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES, emergency_months=6)
    assert alloc.emergency.target == D("1900.00") * 6


# ── Home-purchase bucket — forward savings, does NOT touch €50K ───────────

def test_house_balance_starts_at_zero_when_no_prior_savings():
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES)
    assert alloc.home_purchase.balance == D("0.00")


def test_house_balance_reflects_prior_savings():
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("72000.00"),
        house_savings_already=D("5000.00"),
    )
    assert alloc.home_purchase.balance == D("5000.00")


def test_house_unconfirmed_when_target_none():
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES, home_purchase_target=None)
    assert alloc.home_purchase.status == BucketStatus.UNCONFIRMED


def test_house_underfunded_when_target_set_but_not_reached():
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("72000.00"),
        house_savings_already=D("5000.00"),
    )
    assert alloc.home_purchase.status == BucketStatus.UNDERFUNDED


def test_house_funded_when_savings_reach_target():
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("10000.00"),
        house_savings_already=D("10000.00"),
    )
    assert alloc.home_purchase.status == BucketStatus.FUNDED


# ── Emergency savings are NEVER used for house purchase ──────────────────

def test_emergency_savings_not_consumed_by_house():
    """Core model constraint: existing savings stay as emergency buffer."""
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("72000.00"),
        house_savings_already=D("0.00"),
    )
    # Emergency buffer still equals full savings
    assert alloc.emergency.balance == TOTAL_SAVINGS
    # House bucket shows 0 (nothing saved yet from surplus)
    assert alloc.home_purchase.balance == D("0.00")


# ── Surplus plan ──────────────────────────────────────────────────────────

def test_surplus_plan_calculated_when_surplus_and_target_known():
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("72000.00"),
        house_savings_already=D("0.00"),
        monthly_surplus=D("1500.00"),
        home_purchase_horizon_years=3,
    )
    assert alloc.surplus_plan is not None
    # 72000 / 36 months = 2000/month needed, but surplus is only 1500 → 0 for LT
    assert alloc.surplus_plan.monthly_to_long_term == D("0.00")


def test_surplus_plan_has_lt_when_surplus_exceeds_house_rate():
    alloc = allocate_buckets(
        TOTAL_SAVINGS, MONTHLY_EXPENSES,
        home_purchase_target=D("36000.00"),   # smaller target
        house_savings_already=D("0.00"),
        monthly_surplus=D("1500.00"),
        home_purchase_horizon_years=3,        # 36000/36 = 1000/month
    )
    assert alloc.surplus_plan is not None
    assert alloc.surplus_plan.monthly_to_long_term == D("500.00")


# ── Warning emitted when house target unconfirmed ─────────────────────────

def test_warning_when_house_target_unconfirmed():
    alloc = allocate_buckets(TOTAL_SAVINGS, MONTHLY_EXPENSES, home_purchase_target=None)
    assert any("home" in w.lower() or "house" in w.lower() or "target" in w.lower()
               for w in alloc.warnings)
