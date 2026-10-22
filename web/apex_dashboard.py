"""
APEX 2.0 — Streamlit Investment Dashboard
Run: streamlit run web/apex_dashboard.py

Sections:
  1. KPI Row — emergency buffer, monthly surplus, FIRE progress
  2. ETF Price Chart — VWCE / IWDA / IS3N
  3. Monte Carlo Fan Chart — P5–P95 projection to age 47
  4. Live Opportunity Alerts — 7 checks, Gmail send button
  5. Sidebar — profile summary, FSA bar, quick actions, tax calendar
"""
from __future__ import annotations

import subprocess
import sys
import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import streamlit as st
import plotly.graph_objects as go

# Resolve project root so we can import from sibling packages
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web.components import (
    kpi_card, alert_card, fsa_progress_bar,
    monte_carlo_chart, etf_price_chart,
    alert_color,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="APEX — Nitish's Investment Mentor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
  .stMetric > div { background: #1a1a2e; border-radius: 8px; padding: 12px; }
  .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Profile loader ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_profile() -> dict:
    """Load financial_profile.yaml. Returns empty dict if not found."""
    profile_path = os.path.join(ROOT, "data", "financial_profile.yaml")
    try:
        import yaml
        with open(profile_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        st.warning(f"Could not load profile: {e}")
        return {}


def _dec(val, default: str = "0") -> Decimal:
    """Safely convert a profile value to Decimal."""
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return Decimal(default)


# ── Market data loader ────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_etf_history(yf_ticker: str, period: str = "1y"):
    """Fetch ETF price history via yfinance. Returns DataFrame or None."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(period=period)
        if hist.empty:
            return None
        return hist
    except Exception:
        return None


@st.cache_data(ttl=3600)
def load_monte_carlo(monthly_investment_eur: float) -> object:
    """Run Monte Carlo simulation. Cached for 1 hour."""
    try:
        from core.monte_carlo import run_simulation, SimulationConfig
        config = SimulationConfig(
            monthly_investment=Decimal(str(round(monthly_investment_eur, 2))),
            initial_invested=Decimal("0"),
            annual_return_mean=0.07,
            annual_return_std=0.15,
            years=11,
            simulations=1000,
            fire_target=Decimal("600000"),
        )
        return run_simulation(config, seed=42)
    except Exception as e:
        st.error(f"Monte Carlo error: {e}")
        return None


# ── Opportunity scanner ───────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def load_opportunities(profile_date: str) -> list:
    """Scan for triggered opportunities. profile_date used to bust cache on reload."""
    try:
        from notify.opportunity_scanner import scan_all
        # Minimal market_data with no prices — checks date-based triggers only
        # (price-based checks need live data; this runs the safe subset)
        market_data: dict = {"etf_prices": {}, "etf_prev_prices": {},
                              "ecb_rate_current": Decimal("0"), "ecb_rate_prev": Decimal("0")}
        profile = {}
        portfolio: dict = {"current_weights": {}, "target_weights": {}}
        return scan_all(market_data, profile, portfolio, today=date.today())
    except Exception as e:
        return []


# ═════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ═════════════════════════════════════════════════════════════════════════════

profile = load_profile()

# Extract key values
savings_sc = _dec(
    (profile.get("savings") or {}).get("scalable_capital_tagesgeld", {}).get("balance"), "50000"
)
net_monthly     = _dec((profile.get("income") or {}).get("net_monthly"), "4315.34")
kindergeld      = _dec((profile.get("income") or {}).get("kindergeld_monthly"), "259")
expenses_items  = profile.get("expenses") or {}
expenses_total  = sum(
    _dec(v) for k, v in expenses_items.items()
    if isinstance(v, (int, float)) and k not in ("unlisted_expense_warning",)
)
monthly_surplus = net_monthly + kindergeld - expenses_total
fsa_total       = _dec((profile.get("tax") or {}).get("sparer_pauschbetrag_eur"), "2000")
fsa_used        = Decimal("0")        # not yet invested — no events to trigger
profile_date    = (profile.get("meta") or {}).get("profile_date", "unknown")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 APEX v2.0")
    st.markdown("---")
    st.markdown(f"**Profile:** Nitish Bidwe")
    st.markdown(f"**Location:** Ingolstadt, DE")
    st.markdown(f"**Last updated:** {profile_date}")
    st.markdown("---")

    # FSA progress bar
    st.markdown("**Sparer-Pauschbetrag 2024**")
    fsa_progress_bar(fsa_used, fsa_total)
    st.markdown("---")

    # Quick actions
    st.markdown("**Quick Actions**")
    if st.button("🔄 Run Full Report"):
        with st.spinner("Generating report…"):
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(ROOT, "report.py")],
                    capture_output=True, text=True, timeout=30
                )
                st.code(result.stdout or result.stderr, language="text")
            except Exception as e:
                st.error(f"Report failed: {e}")

    if st.button("📧 Send Weekly Digest"):
        with st.spinner("Sending digest…"):
            try:
                from notify.weekly_digest import generate_weekly_digest
                from notify.gmail_alert import send_alert, Opportunity as _O
                body = generate_weekly_digest(
                    profile=profile, market_data={}, portfolio={}
                )
                opp = _O(
                    name="WEEKLY_DIGEST",
                    severity="INFO",
                    subject="📊 APEX Weekly Investment Digest",
                    body=body,
                )
                from notify.gmail_alert import send_alert
                ok = send_alert(opp)
                st.success("Digest sent!" if ok else "Sent (dry run — set GMAIL_APP_PASSWORD to email)")
            except Exception as e:
                st.error(f"Digest error: {e}")

    if st.button("📡 Refresh Market Data"):
        load_etf_history.clear()
        load_monte_carlo.clear()
        load_opportunities.clear()
        st.success("Cache cleared — data will reload.")

    st.markdown("---")

    # Tax calendar
    st.markdown("**Tax Calendar**")
    tax = profile.get("tax") or {}
    steuer = tax.get("steuererklarung_2024", "UNKNOWN")
    fsa_scalable = tax.get("freistellungsauftrag_scalable")
    steuer_icon  = "⚠️" if "NOT FILED" in str(steuer) else "✅"
    fsa_icon     = "⚠️" if fsa_scalable is None else "✅"

    st.markdown(f"• Steuererklärung 2024: {steuer_icon} {'NOT FILED' if 'NOT FILED' in str(steuer) else 'Filed'}")
    st.markdown(f"• Freistellungsauftrag Scalable: {fsa_icon} {'Not filed' if fsa_scalable is None else 'Filed'}")
    st.markdown("• Next Vorabpauschale: Jan 2025")


# ── Section 1: KPI Row ────────────────────────────────────────────────────────
st.markdown("## 💰 Financial Overview")
col1, col2, col3 = st.columns(3)

with col1:
    months_covered = int(savings_sc / expenses_total) if expenses_total > 0 else 0
    kpi_card(
        label="Emergency Buffer",
        value=f"€{savings_sc:,.0f}",
        status=f"✅ {months_covered} months covered (locked)",
        help_text="Scalable Capital Tagesgeld @ 2.5% — emergency reserve, never invest",
    )

with col2:
    surplus_str = f"€{monthly_surplus:,.0f}"
    kpi_card(
        label="Monthly Surplus",
        value=surplus_str,
        status="⚠️ Unverified — unlisted expenses likely",
        help_text="Net income + Kindergeld minus listed expenses only. Run 3-month bank review.",
    )

with col3:
    fire_target = Decimal("600000")
    current_invested = Decimal("0")
    pct = int(current_invested / fire_target * 100)
    kpi_card(
        label="FIRE Progress",
        value=f"€{current_invested:,.0f} / €{fire_target:,.0f}",
        status=f"{pct}% — not yet started",
        help_text="Target: €600K by age 47 (4% rule × annual expenses × 25)",
    )

st.markdown("---")

# ── Section 2: ETF Price Chart ────────────────────────────────────────────────
st.markdown("## 📊 ETF Prices")

ETF_DISPLAY = {
    "VWCE": "VWCE.DE",
    "IWDA": "IWDA.AS",
    "IS3N": "IS3N.DE",
}

col_etf, col_period = st.columns([3, 1])
with col_etf:
    selected_etf = st.selectbox("Select ETF", list(ETF_DISPLAY.keys()), index=0)
with col_period:
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=3,
                          format_func=lambda p: {"1mo":"1M","3mo":"3M","6mo":"6M","1y":"1Y"}[p])

yf_ticker = ETF_DISPLAY[selected_etf]
with st.spinner(f"Loading {selected_etf} prices…"):
    hist = load_etf_history(yf_ticker, period)

fig_etf = etf_price_chart(selected_etf, hist)
st.plotly_chart(fig_etf, use_container_width=True)

if hist is not None and len(hist) > 0:
    last_close = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close
    delta_pct  = (last_close - prev_close) / prev_close * 100 if prev_close else 0
    col_p, col_h, col_l = st.columns(3)
    col_p.metric("Last Close", f"€{last_close:.2f}", f"{delta_pct:+.2f}%")
    col_h.metric("52w High",   f"€{float(hist['Close'].max()):.2f}")
    col_l.metric("52w Low",    f"€{float(hist['Close'].min()):.2f}")

st.markdown("---")

# ── Section 3: Monte Carlo Fan Chart ─────────────────────────────────────────
st.markdown("## 🎲 Monte Carlo FIRE Projection")

invest_slider = st.slider(
    "Monthly investment (€)",
    min_value=0, max_value=3500, value=500, step=50,
    help="Adjust to see how different monthly amounts change FIRE probability",
)

with st.spinner("Running 1,000 simulations…"):
    mc_result = load_monte_carlo(float(invest_slider))

if mc_result is not None:
    fig_mc = monte_carlo_chart(mc_result, start_age=36)
    st.plotly_chart(fig_mc, use_container_width=True)

    fire_prob = float(mc_result.fire_probability) * 100
    median_age = mc_result.median_fire_age
    p50_final  = mc_result.p50[-1]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        f"FIRE probability by age 47",
        f"{fire_prob:.1f}%",
        help="% of simulations where portfolio reaches €600K by age 47",
    )
    col_b.metric(
        "Median portfolio at age 47",
        f"€{float(p50_final):,.0f}",
    )
    col_c.metric(
        "Median FIRE age",
        str(median_age) if median_age else "After age 86",
        help="Age at which 50% of simulations reach €600K",
    )

    if fire_prob < 10:
        st.info(
            f"💡 At €{invest_slider}/month: only {fire_prob:.1f}% chance of FIRE by 47. "
            f"Slide to ≈€3,200/month to reach 50% probability — requires salary growth first."
        )
else:
    st.warning("Monte Carlo simulation failed. Check logs.")

st.markdown("---")

# ── Section 4: Live Opportunity Alerts ───────────────────────────────────────
st.markdown("## 🔔 Live Alerts")

opportunities = load_opportunities(profile_date)

if not opportunities:
    st.success("✅ No alerts — all clear")
else:
    st.warning(f"{len(opportunities)} alert(s) triggered")
    for opp in opportunities:
        alert_card(opp)

    if st.button("📨 Send All Alerts via Email"):
        with st.spinner("Sending…"):
            try:
                from notify.gmail_alert import send_all_alerts
                sent = send_all_alerts(opportunities, dry_run=False)
                st.success(f"Sent {sent} alert(s). Check {os.getenv('GMAIL_APP_PASSWORD', 'dry-run mode — set GMAIL_APP_PASSWORD to send')}.")
            except Exception as e:
                st.error(f"Send failed: {e}")

st.markdown("---")

# ── Section 5: Chat with APEX ────────────────────────────────────────────────
st.markdown("## 💬 Chat with APEX")
st.caption("Ask your investment mentor anything — runs locally via Ollama when available, falls back to Gemini")

if "apex_session_id" not in st.session_state:
    import uuid as _uuid
    st.session_state.apex_session_id = str(_uuid.uuid4())
if "apex_messages" not in st.session_state:
    st.session_state.apex_messages = []

# Render chat history
for _msg in st.session_state.apex_messages:
    with st.chat_message(_msg["role"]):
        st.markdown(_msg["content"])

# Chat input
if _prompt := st.chat_input("Ask APEX about your investments, taxes, FIRE plan…"):
    st.session_state.apex_messages.append({"role": "user", "content": _prompt})
    with st.chat_message("user"):
        st.markdown(_prompt)

    with st.chat_message("assistant"):
        with st.spinner("APEX thinking…"):
            try:
                import sys as _sys
                import os as _os
                _sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
                from agent.apex_agent import chat as _apex_chat
                _reply = _apex_chat(_prompt, session_id=st.session_state.apex_session_id)
            except RuntimeError as _e:
                _reply = (
                    f"⚠️ No LLM provider available: {_e}\n\n"
                    "**To enable chat:**\n"
                    "- Mac Mini M4: `ollama run qwen3.8b:27b`\n"
                    "- Linux: `ollama run qwen3:8b`\n"
                    "- Cloud: `export GEMINI_API_KEY=your_key`"
                )
            except Exception as _e:
                _reply = f"⚠️ Error: {_e}"
        st.markdown(_reply)

    st.session_state.apex_messages.append({"role": "assistant", "content": _reply})

    if st.button("🗑️ Clear chat history"):
        st.session_state.apex_messages = []
        st.rerun()

st.markdown("---")
st.caption(
    "APEX v2.0 · Personal Investment Mentor · "
    f"Data as of {profile_date} · "
    "Not financial advice — verify all figures before acting."
)
