"""
Tests for web/components.py — pure functions only.
Does NOT import streamlit or call st.* (those functions are thin rendering wrappers).
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from decimal import Decimal
import plotly.graph_objects as go
import pytest

from web.components import (
    monte_carlo_chart,
    etf_price_chart,
    alert_color,
    alert_bg,
    fsa_fraction,
    SEVERITY_COLORS,
    SEVERITY_BG,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_mc_result():
    """Minimal MonteCarloResult-like object for chart tests."""
    from core.monte_carlo import run_simulation, SimulationConfig
    config = SimulationConfig(
        monthly_investment=Decimal("500"),
        initial_invested=Decimal("0"),
        annual_return_mean=0.07,
        annual_return_std=0.15,
        years=3,
        simulations=50,   # fast for tests
        fire_target=Decimal("600000"),
    )
    return run_simulation(config, seed=42)


def _make_hist_df():
    """Create a minimal price history DataFrame."""
    import pandas as pd
    import numpy as np
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    prices = 100 + np.arange(30, dtype=float)
    return pd.DataFrame({"Close": prices}, index=dates)


# ── monte_carlo_chart ─────────────────────────────────────────────────────────

def test_monte_carlo_chart_returns_figure():
    result = _make_mc_result()
    fig = monte_carlo_chart(result, start_age=36)
    assert isinstance(fig, go.Figure)


def test_monte_carlo_chart_has_traces():
    result = _make_mc_result()
    fig = monte_carlo_chart(result, start_age=36)
    # Should have at least 3 traces: outer band, inner band, P50 line
    assert len(fig.data) >= 3


def test_monte_carlo_chart_age_range():
    result = _make_mc_result()
    fig = monte_carlo_chart(result, start_age=36)
    # P50 trace is last scatter with x values
    p50_trace = fig.data[-1]
    assert p50_trace.x[0] == 36
    assert p50_trace.x[-1] == 36 + result.config.years


def test_monte_carlo_chart_has_fire_line():
    result = _make_mc_result()
    fig = monte_carlo_chart(result, start_age=36)
    # hline creates a shape in layout
    assert fig.layout.shapes is not None and len(fig.layout.shapes) >= 1


# ── etf_price_chart ───────────────────────────────────────────────────────────

def test_etf_price_chart_returns_figure_with_data():
    hist = _make_hist_df()
    fig = etf_price_chart("VWCE", hist)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_etf_price_chart_empty_returns_figure():
    fig = etf_price_chart("VWCE", None)
    assert isinstance(fig, go.Figure)
    # Should show annotation instead of data
    assert len(fig.layout.annotations) >= 1


def test_etf_price_chart_has_52w_lines():
    hist = _make_hist_df()
    fig = etf_price_chart("VWCE", hist)
    # Two hlines = two shapes (high + low)
    assert fig.layout.shapes is not None and len(fig.layout.shapes) >= 2


def test_etf_price_chart_empty_df_returns_figure():
    import pandas as pd
    empty = pd.DataFrame({"Close": []})
    fig = etf_price_chart("IWDA", empty)
    assert isinstance(fig, go.Figure)


# ── Alert color mapping ───────────────────────────────────────────────────────

def test_alert_color_action_is_red():
    c = alert_color("ACTION")
    assert c.lower().startswith("#ff") or "red" in c.lower()
    assert c == SEVERITY_COLORS["ACTION"]


def test_alert_color_warn_is_orange():
    c = alert_color("WARN")
    assert c == SEVERITY_COLORS["WARN"]
    # Not the same as ACTION
    assert c != alert_color("ACTION")


def test_alert_color_info_is_blue():
    c = alert_color("INFO")
    assert c == SEVERITY_COLORS["INFO"]
    assert c != alert_color("ACTION")
    assert c != alert_color("WARN")


def test_alert_bg_all_three_severities():
    for sev in ("ACTION", "WARN", "INFO"):
        bg = alert_bg(sev)
        assert bg.startswith("#")
        assert len(bg) in (7, 9)  # #RRGGBB or #RRGGBBAA


# ── FSA fraction ─────────────────────────────────────────────────────────────

def test_fsa_fraction_zero_used():
    assert fsa_fraction(Decimal("0"), Decimal("2000")) == pytest.approx(0.0)


def test_fsa_fraction_full():
    assert fsa_fraction(Decimal("2000"), Decimal("2000")) == pytest.approx(1.0)


def test_fsa_fraction_half():
    assert fsa_fraction(Decimal("1000"), Decimal("2000")) == pytest.approx(0.5)


def test_fsa_fraction_zero_total():
    # Should not raise, returns 0.0
    assert fsa_fraction(Decimal("500"), Decimal("0")) == pytest.approx(0.0)


def test_fsa_fraction_clamps_to_one():
    # Over-used (shouldn't happen but must not return >1)
    val = fsa_fraction(Decimal("3000"), Decimal("2000"))
    assert val <= 1.0


def test_fsa_fraction_clamps_to_zero():
    # Negative used (edge case)
    val = fsa_fraction(Decimal("-100"), Decimal("2000"))
    assert val >= 0.0
