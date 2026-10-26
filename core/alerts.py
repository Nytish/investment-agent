"""
alerts.py — Buy signal detection and opportunity alerts.

Analyses ETF prices against historical data to surface actionable buy signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from core.market_data import ETFQuote
from core.profile import PROFILE


@dataclass
class Alert:
    ticker: str
    name: str
    severity: str           # "BUY_SIGNAL" | "WATCH" | "INFO" | "WARNING"
    title: str
    message: str
    action: str
    dip_pct: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def color(self) -> str:
        colors = {
            "BUY_SIGNAL": "#00C850",
            "WATCH": "#FFD700",
            "INFO": "#4A9EFF",
            "WARNING": "#FF6B6B",
        }
        return colors.get(self.severity, "#888888")

    @property
    def icon(self) -> str:
        icons = {
            "BUY_SIGNAL": "🟢",
            "WATCH": "🟡",
            "INFO": "🔵",
            "WARNING": "🔴",
        }
        return icons.get(self.severity, "⚪")


def scan_for_alerts(quotes: dict[str, Optional[ETFQuote]]) -> list[Alert]:
    """
    Scan all ETF quotes and produce actionable alerts.

    Thresholds:
    - Strong buy: >5% below 52-week high + negative day
    - Watch: >3% below 52-week high
    - Weekly dip: day change < -2%
    """
    alerts: list[Alert] = []

    for ticker, quote in quotes.items():
        if quote is None:
            continue

        dip_from_high = quote.dip_pct_from_high
        day_change = quote.change_pct

        # Strong buy signal: significant dip from high
        if dip_from_high >= 10:
            alerts.append(Alert(
                ticker=ticker,
                name=quote.name,
                severity="BUY_SIGNAL",
                title=f"Strong DCA opportunity: {ticker}",
                message=(
                    f"{ticker} is {dip_from_high:.1f}% below its 52-week high "
                    f"(€{quote.price:.2f} vs high €{quote.week52_high:.2f}). "
                    f"Today: {day_change:+.2f}%."
                ),
                action=f"Consider increasing monthly DCA above €{PROFILE.etf_plan_monthly:,.0f}",
                dip_pct=dip_from_high,
            ))
        elif dip_from_high >= 5:
            alerts.append(Alert(
                ticker=ticker,
                name=quote.name,
                severity="BUY_SIGNAL",
                title=f"Buy signal: {ticker} dip",
                message=(
                    f"{ticker} is {dip_from_high:.1f}% below 52-week high "
                    f"(€{quote.price:.2f}). Good entry for DCA."
                ),
                action=f"Good time to start/increase DCA — current planned €{PROFILE.etf_plan_monthly:,.0f}/month",
                dip_pct=dip_from_high,
            ))
        elif dip_from_high >= 3:
            alerts.append(Alert(
                ticker=ticker,
                name=quote.name,
                severity="WATCH",
                title=f"Watch: {ticker} pulling back",
                message=(
                    f"{ticker} is {dip_from_high:.1f}% below 52-week high. "
                    f"Today: {day_change:+.2f}%. Watching for deeper entry."
                ),
                action="No action needed — maintain planned DCA",
                dip_pct=dip_from_high,
            ))

        # Significant single-day drop
        if day_change <= -3 and dip_from_high < 3:
            alerts.append(Alert(
                ticker=ticker,
                name=quote.name,
                severity="WATCH",
                title=f"Single-day drop: {ticker} {day_change:+.2f}%",
                message=(
                    f"{ticker} dropped {abs(day_change):.2f}% today "
                    f"to €{quote.price:.2f}. Monitor tomorrow."
                ),
                action="Stick to plan — don't panic sell or over-buy on one day",
                dip_pct=dip_from_high,
            ))

    # Static alerts from profile
    if "NOT" in PROFILE.freistellungsauftrag_scalable.upper():
        interest = PROFILE.freistellung_interest_annual()
        tax_saving = PROFILE.freistellung_tax_saving()
        alerts.append(Alert(
            ticker="—",
            name="Tax Action",
            severity="WARNING",
            title="⚠️ Freistellungsauftrag not filed",
            message=(
                f"You're earning ~€{interest:,.0f}/year interest on Tagesgeld. "
                f"Without Freistellungsauftrag, you'll pay 26.375% tax on it. "
                f"File with Scalable Capital now — saves ~€{tax_saving:,.0f}/year."
            ),
            action="File Freistellungsauftrag (€2,000) at scalable.capital → Settings → Tax",
        ))

    if PROFILE.etf_invested == 0:
        alerts.append(Alert(
            ticker="VWCE.DE",
            name="Getting Started",
            severity="INFO",
            title="Start your ETF savings plan",
            message=(
                f"You have €{PROFILE.monthly_surplus:,.0f}/month surplus and €0 invested. "
                f"Setting up a €{PROFILE.etf_plan_monthly:,.0f}/month VWCE.DE DCA on Trade Republic "
                f"takes about 5 minutes."
            ),
            action="Open Trade Republic → ETF Savings Plan → VWCE.DE → €500/month → Execute",
        ))

    return sorted(alerts, key=lambda a: (
        {"BUY_SIGNAL": 0, "WARNING": 1, "WATCH": 2, "INFO": 3}.get(a.severity, 4)
    ))
