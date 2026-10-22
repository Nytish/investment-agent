"""
APEX 2.0 — Opportunity Scanner
Checks 7 market/tax/portfolio conditions. Returns Opportunity dataclass if triggered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date


VALID_SEVERITIES = frozenset({"INFO", "WARN", "ACTION"})


@dataclass
class Opportunity:
    name: str                    # e.g. "VWCE_DROP_5PCT"
    severity: str                # "INFO" | "WARN" | "ACTION"
    subject: str                 # email subject line
    body: str                    # email body (plain text)
    ticker: str | None = None    # relevant ETF ticker if applicable

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}, got {self.severity!r}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_etf_drop(
    ticker: str,
    current_price: Decimal,
    prev_price: Decimal,
    threshold: Decimal = Decimal("0.05"),
) -> Opportunity | None:
    """Triggers if price dropped > threshold since yesterday."""
    if prev_price <= Decimal("0"):
        return None
    drop = (prev_price - current_price) / prev_price
    if drop <= threshold:
        return None
    pct = drop * 100
    return Opportunity(
        name=f"{ticker}_DROP_{int(pct)}PCT",
        severity="ACTION",
        subject=f"⚠️ {ticker} dropped {pct:.1f}% today — consider buying",
        ticker=ticker,
        body=(
            f"Hi Nitish,\n\n"
            f"{ticker} dropped from €{prev_price:.2f} to €{current_price:.2f} today (-{pct:.1f}%).\n\n"
            f"This is a buy opportunity for your long-term bucket.\n"
            f"At your current investment pace, consider adding an extra €250–500 now.\n\n"
            f"Tax note: Purchases at a lower cost basis reduce future Vorabpauschale.\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_portfolio_drift(
    current_weights: dict[str, Decimal],
    target_weights: dict[str, Decimal],
    threshold: Decimal = Decimal("0.05"),
) -> Opportunity | None:
    """Triggers if any ETF drifts >threshold from target allocation."""
    drifted = []
    for ticker, target in target_weights.items():
        current = current_weights.get(ticker, Decimal("0"))
        drift = abs(current - target)
        if drift > threshold:
            direction = "overweight" if current > target else "underweight"
            drifted.append(
                f"  {ticker}: {float(current)*100:.1f}% actual vs {float(target)*100:.1f}% target "
                f"({direction}, drift {float(drift)*100:.1f}%)"
            )
    if not drifted:
        return None
    lines = "\n".join(drifted)
    return Opportunity(
        name="PORTFOLIO_DRIFT",
        severity="WARN",
        subject="🔄 Portfolio drift >5% — rebalance recommended",
        body=(
            f"Hi Nitish,\n\n"
            f"Your portfolio has drifted from target allocation:\n\n"
            f"{lines}\n\n"
            f"Consider rebalancing by directing new investments to underweight positions.\n"
            f"Avoid selling — use new contributions to rebalance (tax-efficient).\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_vorabpauschale_january(today: date) -> Opportunity | None:
    """Triggers in first 7 days of January — reminder to check FSA."""
    if today.month != 1 or today.day > 7:
        return None
    return Opportunity(
        name="VORABPAUSCHALE_JANUARY",
        severity="ACTION",
        subject="📅 January: Vorabpauschale will be deducted — check Freistellungsauftrag",
        body=(
            f"Hi Nitish,\n\n"
            f"It's January — Vorabpauschale will be calculated and deducted by your broker.\n\n"
            f"Action items:\n"
            f"  1. Confirm Freistellungsauftrag is filed with Scalable Capital (€2,000 — married)\n"
            f"  2. Check that FSA covers your expected Vorabpauschale (run: python report.py)\n"
            f"  3. Basiszins for {today.year} will be published by Bundesbank in January — check APEX\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_fsa_low(
    fsa_remaining: Decimal,
    threshold: Decimal = Decimal("200"),
) -> Opportunity | None:
    """Triggers when FSA remaining < threshold."""
    if fsa_remaining >= threshold:
        return None
    return Opportunity(
        name="FSA_LOW",
        severity="WARN",
        subject=f"⚠️ Freistellungsauftrag almost exhausted (€{fsa_remaining:.2f} remaining)",
        body=(
            f"Hi Nitish,\n\n"
            f"Your Sparer-Pauschbetrag (FSA) has only €{fsa_remaining:.2f} remaining.\n\n"
            f"Any further interest or Vorabpauschale will be taxed at 26.375% (Abgeltungsteuer).\n\n"
            f"Options:\n"
            f"  • This is normal if your portfolio is growing — no action needed\n"
            f"  • FSA resets to €2,000 on 1 January — tax drag is temporary\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_tagesgeld_rate_drop(
    current_rate: Decimal,
    prev_rate: Decimal,
    threshold: Decimal = Decimal("0.005"),
) -> Opportunity | None:
    """Triggers if Tagesgeld/ECB rate drops >0.5% — consider shifting to ETF sooner."""
    if prev_rate <= Decimal("0"):
        return None
    drop = prev_rate - current_rate
    if drop <= threshold:
        return None
    return Opportunity(
        name="TAGESGELD_RATE_DROP",
        severity="INFO",
        subject=f"📉 ECB rate dropped {float(drop)*100:.2f}% — reconsider Tagesgeld allocation",
        body=(
            f"Hi Nitish,\n\n"
            f"The ECB deposit rate dropped from {float(prev_rate)*100:.2f}% to {float(current_rate)*100:.2f}%.\n\n"
            f"Your Scalable Capital Tagesgeld rate will likely follow.\n\n"
            f"At lower Tagesgeld rates, the expected return gap vs global equity ETFs widens.\n"
            f"Consider: begin your VWCE investment plan sooner if you haven't already.\n\n"
            f"Emergency buffer (€50,000) stays in Tagesgeld — this concerns your surplus only.\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_steuererklarung_deadline(today: date) -> Opportunity | None:
    """Triggers Jan 1 – Jul 31 — Steuererklärung reminder."""
    if today.month < 1 or today.month > 7:
        return None
    # Aug 1 or later: no trigger
    if today.month == 7 and today.day > 31:
        return None
    year = today.year - 1  # prior tax year
    days_left = (date(today.year, 7, 31) - today).days
    return Opportunity(
        name="STEUERERKLARUNG_DEADLINE",
        severity="ACTION",
        subject=f"📋 Steuererklärung {year} due by 31 July — {days_left} days left",
        body=(
            f"Hi Nitish,\n\n"
            f"Steuererklärung {year} deadline: 31 July {today.year} ({days_left} days away).\n\n"
            f"Key deductions to claim:\n"
            f"  • Werbungskosten (commuting, home office)\n"
            f"  • Kinderbetreuungskosten (childcare)\n"
            f"  • Sprachkurs costs (German B1 — partially deductible as Fortbildung)\n"
            f"  • Capital gains / interest income (if not already deducted at source)\n\n"
            f"Tool: ELSTER (elster.de) or use a Steuerberater.\n\n"
            f"APEX — your investment mentor"
        ),
    )


def check_new_year_rebalance(today: date) -> Opportunity | None:
    """Triggers on 2 January (first working day of year) — annual rebalance reminder."""
    if today.month != 1 or today.day != 2:
        return None
    return Opportunity(
        name="NEW_YEAR_REBALANCE",
        severity="INFO",
        subject=f"🎯 New Year {today.year}: annual portfolio review",
        body=(
            f"Hi Nitish,\n\n"
            f"Happy New Year! Time for your annual portfolio review.\n\n"
            f"Checklist:\n"
            f"  1. Review target allocation — still correct for your risk profile?\n"
            f"  2. Check Freistellungsauftrag filed with each broker (resets 1 Jan)\n"
            f"  3. Vorabpauschale for {today.year - 1} will be calculated — check APEX tax report\n"
            f"  4. Rebalance if any ETF drifted >5% from target\n"
            f"  5. Update monthly investment amount if surplus changed\n\n"
            f"APEX — your investment mentor"
        ),
    )


# ---------------------------------------------------------------------------
# Aggregate scanner
# ---------------------------------------------------------------------------

def scan_all(
    market_data: dict,
    profile: dict,
    portfolio: dict,
    today: date | None = None,
) -> list[Opportunity]:
    """
    Run all 7 checks. Returns list of triggered Opportunity objects (empty if none).

    Expected keys:
      market_data:
        etf_prices: dict[str, Decimal]       current prices
        etf_prev_prices: dict[str, Decimal]  previous day prices
        ecb_rate_current: Decimal
        ecb_rate_prev: Decimal
      profile:
        fsa_remaining: Decimal
      portfolio:
        current_weights: dict[str, Decimal]
        target_weights: dict[str, Decimal]
    """
    if today is None:
        today = date.today()

    results: list[Opportunity] = []

    # 1. ETF drops
    current_prices: dict[str, Decimal] = market_data.get("etf_prices", {})
    prev_prices: dict[str, Decimal] = market_data.get("etf_prev_prices", {})
    for ticker, current_price in current_prices.items():
        prev = prev_prices.get(ticker)
        if prev is not None:
            opp = check_etf_drop(ticker, current_price, prev)
            if opp:
                results.append(opp)

    # 2. Portfolio drift
    current_weights: dict[str, Decimal] = portfolio.get("current_weights", {})
    target_weights: dict[str, Decimal] = portfolio.get("target_weights", {})
    if current_weights and target_weights:
        opp = check_portfolio_drift(current_weights, target_weights)
        if opp:
            results.append(opp)

    # 3. Vorabpauschale January
    opp = check_vorabpauschale_january(today)
    if opp:
        results.append(opp)

    # 4. FSA low
    fsa_remaining = profile.get("fsa_remaining")
    if fsa_remaining is not None:
        opp = check_fsa_low(Decimal(str(fsa_remaining)))
        if opp:
            results.append(opp)

    # 5. Tagesgeld rate drop
    ecb_current = market_data.get("ecb_rate_current")
    ecb_prev = market_data.get("ecb_rate_prev")
    if ecb_current is not None and ecb_prev is not None:
        opp = check_tagesgeld_rate_drop(
            Decimal(str(ecb_current)), Decimal(str(ecb_prev))
        )
        if opp:
            results.append(opp)

    # 6. Steuererklärung deadline
    opp = check_steuererklarung_deadline(today)
    if opp:
        results.append(opp)

    # 7. New year rebalance
    opp = check_new_year_rebalance(today)
    if opp:
        results.append(opp)

    return results
