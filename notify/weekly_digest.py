"""
APEX 2.0 — Weekly Sunday Digest Generator

Produces a plain-text email body summarising:
  - Portfolio value change this week
  - ETF prices vs 52-week context
  - Tagesgeld rate
  - FSA status
  - Upcoming tax events
  - 3 suggested actions
  - Monte Carlo P50 projection snapshot
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


def generate_weekly_digest(
    profile: dict[str, Any],
    market_data: dict[str, Any],
    portfolio: dict[str, Any],
    today: date | None = None,
) -> str:
    """
    Generate plain-text weekly Sunday digest.

    Expected keys:
      profile:
        name: str
        fsa_total: Decimal
        fsa_used: Decimal
        fsa_remaining: Decimal
        tagesgeld_rate: Decimal          current Tagesgeld rate (e.g. 0.025)
        steuererklarung_filed: bool
      market_data:
        etf_prices: dict[str, Decimal]   ticker → current price
        etf_week_ago_prices: dict[str, Decimal]
        etf_52w_high: dict[str, Decimal]
        etf_52w_low: dict[str, Decimal]
        ecb_rate: Decimal
      portfolio:
        total_value: Decimal
        total_value_week_ago: Decimal
        current_weights: dict[str, Decimal]
        target_weights: dict[str, Decimal]
      Optional: monte_carlo_p50_at_target_age: Decimal
    """
    if today is None:
        today = date.today()

    name = profile.get("name", "Nitish")
    lines: list[str] = []

    lines.append(f"APEX Weekly Digest — {today.strftime('%A, %d %B %Y')}")
    lines.append("=" * 56)

    # ── Week summary ────────────────────────────────────────────
    total_now = Decimal(str(portfolio.get("total_value", 0)))
    total_prev = Decimal(str(portfolio.get("total_value_week_ago", 0)))
    if total_prev > 0:
        change = total_now - total_prev
        pct = change / total_prev * 100
        sign = "+" if change >= 0 else ""
        lines.append(f"\n📊 PORTFOLIO WEEK SUMMARY")
        lines.append(f"   Total value:   €{total_now:,.2f}")
        lines.append(f"   Week change:   {sign}€{change:,.2f} ({sign}{pct:.2f}%)")
    else:
        lines.append(f"\n📊 PORTFOLIO")
        lines.append(f"   Total value:   €{total_now:,.2f}")
        lines.append(f"   (No prior week data — first run?)")

    # ── ETF prices ──────────────────────────────────────────────
    etf_prices: dict[str, Decimal] = market_data.get("etf_prices", {})
    etf_prev: dict[str, Decimal] = market_data.get("etf_week_ago_prices", {})
    etf_52h: dict[str, Decimal] = market_data.get("etf_52w_high", {})
    etf_52l: dict[str, Decimal] = market_data.get("etf_52w_low", {})

    if etf_prices:
        lines.append(f"\n📈 ETF PRICES")
        for ticker, price in etf_prices.items():
            row = f"   {ticker:<6} €{price:>8.2f}"
            prev = etf_prev.get(ticker)
            if prev and prev > 0:
                wk_chg = (price - prev) / prev * 100
                sign = "+" if wk_chg >= 0 else ""
                row += f"  ({sign}{wk_chg:.2f}% WoW)"
            hi = etf_52h.get(ticker)
            lo = etf_52l.get(ticker)
            if hi and lo and hi > 0:
                vs_high = (price - hi) / hi * 100
                row += f"  [52w: €{lo:.2f}–€{hi:.2f}, {vs_high:.1f}% from high]"
            lines.append(row)

    # ── Tagesgeld rate ──────────────────────────────────────────
    tagesgeld_rate = profile.get("tagesgeld_rate")
    ecb_rate = market_data.get("ecb_rate")
    lines.append(f"\n🏦 SAVINGS RATES")
    if tagesgeld_rate is not None:
        lines.append(f"   Scalable Tagesgeld:  {float(tagesgeld_rate)*100:.2f}% p.a.")
    if ecb_rate is not None:
        lines.append(f"   ECB deposit rate:    {float(ecb_rate)*100:.2f}%")

    # ── FSA status ──────────────────────────────────────────────
    fsa_total = Decimal(str(profile.get("fsa_total", 2000)))
    fsa_used = Decimal(str(profile.get("fsa_used", 0)))
    fsa_remaining = Decimal(str(profile.get("fsa_remaining", fsa_total - fsa_used)))
    used_pct = fsa_used / fsa_total * 100 if fsa_total > 0 else Decimal("0")
    bar_filled = int(used_pct / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    lines.append(f"\n🧾 FREISTELLUNGSAUFTRAG (FSA)")
    lines.append(f"   Used:      €{fsa_used:>8.2f} / €{fsa_total:.2f}")
    lines.append(f"   Remaining: €{fsa_remaining:>8.2f}  [{bar}] {float(used_pct):.0f}%")

    # ── Upcoming tax events ─────────────────────────────────────
    lines.append(f"\n📅 TAX CALENDAR")
    if today.month == 12:
        lines.append(f"   ⚠️  December: check FSA fully used before year-end")
    if today.month == 1 and today.day <= 7:
        lines.append(f"   🔴 January: Vorabpauschale deduction imminent — confirm FSA")
    if 1 <= today.month <= 7:
        year = today.year - 1
        days_left = (date(today.year, 7, 31) - today).days
        filed = profile.get("steuererklarung_filed", False)
        status = "✅ filed" if filed else f"❌ NOT filed — {days_left} days to deadline"
        lines.append(f"   Steuererklärung {year}: {status}")
    else:
        lines.append(f"   Next deadline: Steuererklärung {today.year - 1} by 31 July {today.year}")

    # ── Monte Carlo snapshot ────────────────────────────────────
    mc_p50 = portfolio.get("monte_carlo_p50_at_target_age")
    if mc_p50 is not None:
        mc_p50 = Decimal(str(mc_p50))
        fire_target = Decimal(str(profile.get("fire_target", 600000)))
        pct_of_target = mc_p50 / fire_target * 100 if fire_target > 0 else Decimal("0")
        lines.append(f"\n🎯 FIRE PROJECTION (Monte Carlo P50, age 47)")
        lines.append(f"   Median outcome:  €{mc_p50:,.0f}")
        lines.append(f"   FIRE target:     €{fire_target:,.0f}")
        lines.append(f"   Progress:        {float(pct_of_target):.1f}% of target")

    # ── 3 suggested actions ─────────────────────────────────────
    actions: list[str] = _suggest_actions(profile, market_data, portfolio, today)
    lines.append(f"\n✅ 3 ACTIONS THIS WEEK")
    for i, action in enumerate(actions[:3], 1):
        lines.append(f"   {i}. {action}")

    lines.append(f"\n{'─' * 56}")
    lines.append(f"APEX — your personal investment mentor")
    lines.append(f"Run `python report.py` for the full analysis.")

    return "\n".join(lines)


def _suggest_actions(
    profile: dict,
    market_data: dict,
    portfolio: dict,
    today: date,
) -> list[str]:
    """Pick 3 context-aware actions."""
    actions: list[str] = []

    # Not investing yet?
    total = Decimal(str(portfolio.get("total_value", 0)))
    if total == 0:
        actions.append("Start VWCE savings plan on Trade Republic (min €10/month to begin)")

    # FSA not filed?
    fsa_remaining = Decimal(str(profile.get("fsa_remaining", 2000)))
    if fsa_remaining >= Decimal("1999"):
        actions.append("File Freistellungsauftrag with Scalable Capital (€2,000 — married)")

    # Steuererklärung overdue?
    if 1 <= today.month <= 7 and not profile.get("steuererklarung_filed", False):
        actions.append(f"File Steuererklärung {today.year - 1} via ELSTER — deadline 31 July")

    # Portfolio not started — generic advice
    if total == 0 and len(actions) < 3:
        actions.append("Review APEX FIRE projection: how much to invest monthly for age-47 target")

    # Pad to at least 3 generic ones
    defaults = [
        "Review monthly budget — ensure surplus is accurate in profile",
        "Check Scalable Capital Tagesgeld rate — compare with ECB deposit rate",
        "Read one chapter of 'Kommer Souverän investieren' — builds investing confidence",
    ]
    for d in defaults:
        if len(actions) >= 3:
            break
        if d not in actions:
            actions.append(d)

    return actions[:3]
