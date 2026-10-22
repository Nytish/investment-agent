"""Tests for policy.py — APEX 2.0"""
import sys
from pathlib import Path
from decimal import Decimal
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from policy import evaluate_investment_proposal, PolicyVerdict


def base_proposal(**overrides):
    """Fully qualified passing proposal — override individual fields per test."""
    defaults = dict(
        proposed_asset_class="equity",
        proposed_amount_eur=Decimal("2000.00"),
        total_savings=Decimal("35639.91"),
        emergency_balance=Decimal("11400.00"),
        emergency_target=Decimal("11400.00"),
        home_purchase_balance=Decimal("10000.00"),
        home_purchase_target=Decimal("10000.00"),
        home_purchase_horizon_years=5,          # >4 years allows equity
        long_term_balance=Decimal("14239.91"),
        permitted_instruments=["equity", "bond"],
        risk_tolerance="moderate",
        expenses_verified=True,
        surplus_verified=True,
    )
    defaults.update(overrides)
    return defaults


# ── R1: Emergency reserve ─────────────────────────────────────────────────

def test_blocks_when_emergency_underfunded():
    result = evaluate_investment_proposal(**base_proposal(
        emergency_balance=Decimal("5000.00"),
        emergency_target=Decimal("11400.00"),
    ))
    assert result.blocked
    r1 = next(c for c in result.checks if c.rule_id == "R1")
    assert r1.verdict == PolicyVerdict.BLOCK


def test_passes_when_emergency_funded():
    result = evaluate_investment_proposal(**base_proposal())
    r1 = next(c for c in result.checks if c.rule_id == "R1")
    assert r1.verdict == PolicyVerdict.PASS


# ── R2: Home-purchase protection ──────────────────────────────────────────

def test_blocks_when_home_target_unconfirmed():
    result = evaluate_investment_proposal(**base_proposal(
        home_purchase_target=None,
    ))
    assert result.blocked
    r2 = next(c for c in result.checks if c.rule_id == "R2")
    assert r2.verdict == PolicyVerdict.BLOCK


def test_blocks_equity_when_horizon_short():
    result = evaluate_investment_proposal(**base_proposal(
        home_purchase_horizon_years=3,
        proposed_asset_class="equity",
    ))
    assert result.blocked
    r2 = next(c for c in result.checks if c.rule_id == "R2")
    assert r2.verdict == PolicyVerdict.BLOCK


def test_allows_equity_when_horizon_long():
    result = evaluate_investment_proposal(**base_proposal(
        home_purchase_horizon_years=5,
        proposed_asset_class="equity",
    ))
    r2 = next(c for c in result.checks if c.rule_id == "R2")
    assert r2.verdict == PolicyVerdict.PASS


# ── R3: Amount within long-term bucket ────────────────────────────────────

def test_blocks_when_amount_exceeds_long_term_bucket():
    result = evaluate_investment_proposal(**base_proposal(
        proposed_amount_eur=Decimal("50000.00"),
        long_term_balance=Decimal("14239.91"),
    ))
    assert result.blocked
    r3 = next(c for c in result.checks if c.rule_id == "R3")
    assert r3.verdict == PolicyVerdict.BLOCK


# ── R4: Permitted instruments ─────────────────────────────────────────────

def test_blocks_when_no_permitted_instruments():
    result = evaluate_investment_proposal(**base_proposal(permitted_instruments=[]))
    assert result.blocked
    r4 = next(c for c in result.checks if c.rule_id == "R4")
    assert r4.verdict == PolicyVerdict.BLOCK


def test_blocks_when_asset_not_in_permitted_list():
    result = evaluate_investment_proposal(**base_proposal(
        proposed_asset_class="crypto",
        permitted_instruments=["equity", "bond"],
    ))
    assert result.blocked


# ── R5: Risk tolerance ────────────────────────────────────────────────────

def test_blocks_when_risk_tolerance_unknown():
    result = evaluate_investment_proposal(**base_proposal(risk_tolerance=None))
    assert result.blocked


# ── R6: Expenses warning ──────────────────────────────────────────────────

def test_warns_when_expenses_unverified():
    result = evaluate_investment_proposal(**base_proposal(
        expenses_verified=False,
        surplus_verified=False,
    ))
    r6 = next(c for c in result.checks if c.rule_id == "R6")
    assert r6.verdict == PolicyVerdict.WARN


# ── No BUY signal fabrication ─────────────────────────────────────────────

def test_no_action_when_goals_unconfirmed():
    """System must BLOCK when essential inputs are missing — never force a BUY."""
    result = evaluate_investment_proposal(**base_proposal(
        home_purchase_target=None,
        permitted_instruments=[],
        risk_tolerance=None,
    ))
    assert result.overall == PolicyVerdict.BLOCK


def test_overall_pass_when_all_clear():
    result = evaluate_investment_proposal(**base_proposal())
    assert result.overall in (PolicyVerdict.PASS, PolicyVerdict.WARN)
    assert not result.blocked
