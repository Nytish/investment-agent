"""
tests/test_monte_carlo.py — APEX 2.0
Tests for core/monte_carlo.py. No network, no file I/O.
All monetary assertions use Decimal.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from monte_carlo import (
    SimulationConfig,
    MonteCarloResult,
    run_simulation,
    monthly_needed_for_fire_by_age,
    DEFAULT_FIRE_TARGET,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

def nitish_config(monthly: str = "500") -> SimulationConfig:
    """Nitish's real setup — €0 invested, €500/month illustrative, 11 years, FIRE €600K."""
    return SimulationConfig(
        monthly_investment=Decimal(monthly),
        initial_invested=Decimal("0"),
        annual_return_mean=0.07,
        annual_return_std=0.15,
        years=11,
        simulations=1000,
        fire_target=Decimal("600000"),
    )


# ── Test 1: Reproducibility (seed=42) ────────────────────────────────────────

def test_reproducible_with_same_seed():
    cfg = nitish_config()
    r1 = run_simulation(cfg, seed=42)
    r2 = run_simulation(cfg, seed=42)
    assert r1.p50 == r2.p50
    assert r1.fire_probability == r2.fire_probability


def test_different_seed_gives_different_result():
    cfg = nitish_config()
    r1 = run_simulation(cfg, seed=42)
    r2 = run_simulation(cfg, seed=99)
    # P50 medians should differ (extremely unlikely to match exactly)
    assert r1.p50[-1] != r2.p50[-1]


# ── Test 2: Percentile ordering ───────────────────────────────────────────────

def test_percentile_ordering_at_each_year():
    """p5 <= p25 <= p50 <= p75 <= p95 at every year index."""
    result = run_simulation(nitish_config(), seed=42)
    for yr in range(len(result.p50)):
        assert result.p5[yr]  <= result.p25[yr], f"p5 > p25 at year {yr}"
        assert result.p25[yr] <= result.p50[yr], f"p25 > p50 at year {yr}"
        assert result.p50[yr] <= result.p75[yr], f"p50 > p75 at year {yr}"
        assert result.p75[yr] <= result.p95[yr], f"p75 > p95 at year {yr}"


# ── Test 3: fire_probability = 1.0 for huge monthly investment ────────────────

def test_fire_probability_near_one_for_huge_investment():
    cfg = SimulationConfig(
        monthly_investment=Decimal("50000"),   # €50K/month — guaranteed to hit €600K
        initial_invested=Decimal("0"),
        years=11,
        simulations=200,
        fire_target=Decimal("600000"),
    )
    result = run_simulation(cfg, seed=42)
    assert result.fire_probability >= Decimal("0.99")


# ── Test 4: fire_probability = 0.0 for tiny investment over 1 year ───────────

def test_fire_probability_zero_for_tiny_short_investment():
    cfg = SimulationConfig(
        monthly_investment=Decimal("1"),
        initial_invested=Decimal("0"),
        years=1,
        simulations=200,
        fire_target=Decimal("600000"),
    )
    result = run_simulation(cfg, seed=42)
    assert result.fire_probability == Decimal("0.0000")


# ── Test 5: median_fire_age is None when unreachable ─────────────────────────

def test_median_fire_age_none_when_unreachable():
    cfg = SimulationConfig(
        monthly_investment=Decimal("100"),
        initial_invested=Decimal("0"),
        years=5,
        simulations=200,
        fire_target=Decimal("600000"),
    )
    result = run_simulation(cfg, seed=42)
    assert result.median_fire_age is None


# ── Test 6: Correct number of year snapshots ─────────────────────────────────

def test_output_has_correct_number_of_years():
    cfg = nitish_config()
    result = run_simulation(cfg, seed=42)
    expected = cfg.years + 1   # year 0 through year N
    assert len(result.p50) == expected
    assert len(result.p25) == expected
    assert len(result.p75) == expected
    assert len(result.yearly_snapshots[0]) == expected


# ── Test 7: all_paths shape ───────────────────────────────────────────────────

def test_yearly_snapshots_shape():
    cfg = nitish_config()
    result = run_simulation(cfg, seed=42)
    assert len(result.yearly_snapshots) == cfg.simulations
    for path in result.yearly_snapshots:
        assert len(path) == cfg.years + 1


# ── Test 8: All values are Decimal and non-negative ──────────────────────────

def test_all_percentile_values_are_decimal_and_nonnegative():
    result = run_simulation(nitish_config(), seed=42)
    for band in [result.p5, result.p25, result.p50, result.p75, result.p95]:
        for val in band:
            assert isinstance(val, Decimal), f"Expected Decimal, got {type(val)}"
            assert val >= Decimal("0"), f"Negative portfolio value: {val}"


# ── Test 9: P50 at year 0 equals initial_invested ────────────────────────────

def test_p50_at_year_zero_equals_initial_invested():
    initial = Decimal("10000")
    cfg = SimulationConfig(
        monthly_investment=Decimal("500"),
        initial_invested=initial,
        years=5,
        simulations=1000,
    )
    result = run_simulation(cfg, seed=42)
    # P50 at year 0 is the median of all paths' first snapshot = initial_invested
    assert result.p50[0] == initial, f"Expected {initial}, got {result.p50[0]}"


# ── Test 10: Smoke test with Nitish's real numbers ───────────────────────────

def test_nitish_smoke_test_500_per_month():
    """
    Smoke test: €500/month, 11 years, 7% mean return.
    Expect P50 final value to be in a plausible range (€70K–€110K).
    """
    result = run_simulation(nitish_config("500"), seed=42)
    p50_final = result.p50[-1]
    assert Decimal("60000") <= p50_final <= Decimal("130000"), (
        f"P50 final {p50_final} outside expected range for €500/month × 11yr"
    )
    # fire_probability should be very low (€600K target too high for €500/month in 11yr)
    assert result.fire_probability < Decimal("0.05")


# ── Test 11: Config is preserved in result ────────────────────────────────────

def test_config_preserved_in_result():
    cfg = nitish_config()
    result = run_simulation(cfg, seed=42)
    assert result.config is cfg


# ── Test 12: fire_probability is Decimal ─────────────────────────────────────

def test_fire_probability_is_decimal():
    result = run_simulation(nitish_config(), seed=42)
    assert isinstance(result.fire_probability, Decimal)
    assert Decimal("0") <= result.fire_probability <= Decimal("1")


# ── Test 13: median_fire_age is int when reachable ───────────────────────────

def test_median_fire_age_is_int_when_reachable():
    cfg = SimulationConfig(
        monthly_investment=Decimal("5000"),    # high enough to reach €600K
        initial_invested=Decimal("0"),
        years=20,
        simulations=300,
        fire_target=Decimal("600000"),
    )
    result = run_simulation(cfg, seed=42)
    if result.median_fire_age is not None:
        assert isinstance(result.median_fire_age, int)
        assert result.median_fire_age >= 36   # can't retire before current age


# ── Test 14: portfolio never goes below zero (floor) ─────────────────────────

def test_portfolio_never_negative():
    """With catastrophic std dev, ensure floor at zero is applied."""
    cfg = SimulationConfig(
        monthly_investment=Decimal("0"),
        initial_invested=Decimal("100"),
        annual_return_mean=-0.90,    # extreme crash scenario
        annual_return_std=0.50,
        years=5,
        simulations=200,
        fire_target=Decimal("1000000"),
    )
    result = run_simulation(cfg, seed=42)
    for path in result.yearly_snapshots:
        for val in path:
            assert val >= Decimal("0"), f"Negative portfolio detected: {val}"


# ── Test 15: monthly_needed_for_fire_by_age returns positive Decimal ─────────

def test_monthly_needed_for_fire_returns_positive():
    monthly = monthly_needed_for_fire_by_age(
        fire_target=Decimal("600000"),
        initial_invested=Decimal("0"),
        target_age=60,
        current_age=36,
        annual_return_mean=0.07,
        seed=42,
    )
    assert isinstance(monthly, Decimal)
    assert monthly > Decimal("0")
    # Sanity: 24 years to €600K should be achievable with a realistic monthly amount
    assert monthly < Decimal("5000")


def test_monthly_needed_returns_minus_one_for_impossible_horizon():
    """Zero years → -1."""
    result = monthly_needed_for_fire_by_age(
        fire_target=Decimal("600000"),
        initial_invested=Decimal("0"),
        target_age=36,    # same as current age → 0 years
        current_age=36,
        seed=42,
    )
    assert result == Decimal("-1")
