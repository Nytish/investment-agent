"""
APEX 2.0 — Reusable Streamlit UI Components

All functions are pure where possible so they can be unit-tested
without invoking Streamlit (chart builders return go.Figure objects).
Streamlit-rendering helpers (alert_card, fsa_progress_bar, kpi_card)
are thin wrappers that call st.* and are excluded from unit tests.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import plotly.graph_objects as go

if TYPE_CHECKING:
    from core.monte_carlo import MonteCarloResult
    from notify.opportunity_scanner import Opportunity


# ── Color palette ─────────────────────────────────────────────────────────────
SEVERITY_COLORS = {
    "ACTION": "#FF4B4B",   # red
    "WARN":   "#FFA500",   # orange/yellow
    "INFO":   "#1E90FF",   # blue
}

SEVERITY_BG = {
    "ACTION": "#2D0000",
    "WARN":   "#2D1A00",
    "INFO":   "#00112D",
}

FIRE_TARGET_COLOR = "#FFD700"       # gold dashed line
MC_BAND_COLORS = {
    "p95": "rgba(0,200,80,0.12)",
    "p75": "rgba(0,200,80,0.20)",
    "p50": "rgba(0,200,80,0.90)",
    "p25": "rgba(0,200,80,0.20)",
    "p5":  "rgba(0,200,80,0.12)",
}


# ── Chart builders (pure — return go.Figure) ──────────────────────────────────

def monte_carlo_chart(result: "MonteCarloResult", start_age: int = 36) -> go.Figure:
    """
    Fan chart showing P5/P25/P50/P75/P95 portfolio bands over time.
    X-axis: age. Y-axis: EUR portfolio value.
    Horizontal gold dashed line at FIRE target.
    """
    years = result.config.years
    ages = list(range(start_age, start_age + years + 1))

    fig = go.Figure()

    # Outer band P5–P95 (filled area)
    p95_vals = [float(v) for v in result.p95]
    p5_vals  = [float(v) for v in result.p5]
    fig.add_trace(go.Scatter(
        x=ages + ages[::-1],
        y=p95_vals + p5_vals[::-1],
        fill="toself",
        fillcolor=MC_BAND_COLORS["p95"],
        line=dict(color="rgba(0,0,0,0)"),
        name="P5–P95 range",
        showlegend=True,
        hoverinfo="skip",
    ))

    # Inner band P25–P75
    p75_vals = [float(v) for v in result.p75]
    p25_vals = [float(v) for v in result.p25]
    fig.add_trace(go.Scatter(
        x=ages + ages[::-1],
        y=p75_vals + p25_vals[::-1],
        fill="toself",
        fillcolor=MC_BAND_COLORS["p75"],
        line=dict(color="rgba(0,0,0,0)"),
        name="P25–P75 range",
        showlegend=True,
        hoverinfo="skip",
    ))

    # P50 median line
    fig.add_trace(go.Scatter(
        x=ages,
        y=[float(v) for v in result.p50],
        line=dict(color="#00C850", width=2.5),
        name="Median (P50)",
        hovertemplate="Age %{x}<br>Median: €%{y:,.0f}<extra></extra>",
    ))

    # FIRE target line
    fire_val = float(result.config.fire_target)
    fig.add_hline(
        y=fire_val,
        line=dict(color=FIRE_TARGET_COLOR, width=1.5, dash="dash"),
        annotation_text=f"FIRE target €{fire_val:,.0f}",
        annotation_position="top right",
        annotation_font_color=FIRE_TARGET_COLOR,
    )

    fig.update_layout(
        title="Monte Carlo Portfolio Projection (1,000 simulations)",
        xaxis_title="Age",
        yaxis_title="Portfolio Value (€)",
        xaxis=dict(tickmode="linear", dtick=1),
        yaxis=dict(tickformat="€,.0f"),
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font=dict(color="#FAFAFA"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def etf_price_chart(ticker: str, history_df) -> go.Figure:
    """
    Line chart of ETF closing price. history_df must have DatetimeIndex and 'Close' column.
    Shows 52-week high/low as horizontal reference lines.
    Returns empty chart with message if history_df is None or empty.
    """
    fig = go.Figure()

    if history_df is None or len(history_df) == 0:
        fig.add_annotation(
            text="No price data. Run `python -m apex.refresh` to populate cache.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#FFA500", size=14),
        )
        fig.update_layout(
            title=f"{ticker} — No data",
            plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            font=dict(color="#FAFAFA"),
        )
        return fig

    close = history_df["Close"]
    high_52w = float(close.max())
    low_52w  = float(close.min())

    fig.add_trace(go.Scatter(
        x=history_df.index,
        y=close,
        line=dict(color="#00C850", width=1.8),
        name=ticker,
        hovertemplate="%{x|%d %b %Y}<br>Close: €%{y:.2f}<extra></extra>",
    ))

    fig.add_hline(
        y=high_52w,
        line=dict(color="#4CAF50", width=1, dash="dot"),
        annotation_text=f"52w high €{high_52w:.2f}",
        annotation_position="top right",
        annotation_font_color="#4CAF50",
    )
    fig.add_hline(
        y=low_52w,
        line=dict(color="#FF4B4B", width=1, dash="dot"),
        annotation_text=f"52w low €{low_52w:.2f}",
        annotation_position="bottom right",
        annotation_font_color="#FF4B4B",
    )

    fig.update_layout(
        title=f"{ticker} — Price History",
        xaxis_title="Date",
        yaxis_title="Close Price (€)",
        yaxis=dict(tickprefix="€"),
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font=dict(color="#FAFAFA"),
        hovermode="x",
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


# ── Severity helpers (pure) ────────────────────────────────────────────────────

def alert_color(severity: str) -> str:
    """Return hex border color for severity badge."""
    return SEVERITY_COLORS.get(severity, "#888888")


def alert_bg(severity: str) -> str:
    """Return hex background color for alert card."""
    return SEVERITY_BG.get(severity, "#1a1a1a")


def fsa_fraction(used: Decimal, total: Decimal) -> float:
    """Return 0.0–1.0 fraction of FSA used. Returns 0.0 for zero total."""
    if total == Decimal("0"):
        return 0.0
    raw = float(used / total)
    return max(0.0, min(1.0, raw))


# ── Streamlit rendering helpers (call st.* — not unit-testable) ───────────────

def kpi_card(label: str, value: str, status: str, help_text: str = "") -> None:
    """Render a styled KPI metric card using st.metric."""
    import streamlit as st
    st.metric(label=label, value=value, delta=status, help=help_text)


def alert_card(opportunity: "Opportunity") -> None:
    """Render a colored alert card for one Opportunity."""
    import streamlit as st
    color  = alert_color(opportunity.severity)
    bg     = alert_bg(opportunity.severity)
    badge  = f"**[{opportunity.severity}]**"
    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {color};
            background: {bg};
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
        ">
            <span style="color:{color}; font-weight:bold;">{opportunity.severity}</span>
            &nbsp;&nbsp;<strong>{opportunity.subject}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Details"):
        st.text(opportunity.body)


def fsa_progress_bar(used: Decimal, total: Decimal) -> None:
    """Render FSA usage as a labelled progress bar."""
    import streamlit as st
    fraction = fsa_fraction(used, total)
    color = "#FF4B4B" if fraction > 0.9 else ("#FFA500" if fraction > 0.7 else "#00C850")
    st.markdown(
        f"""
        <div style="margin:4px 0 8px 0;">
          <div style="background:#333; border-radius:4px; height:12px;">
            <div style="background:{color}; width:{fraction*100:.1f}%; height:12px; border-radius:4px;"></div>
          </div>
          <small>FSA used: €{used:,.2f} / €{total:,.2f}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
