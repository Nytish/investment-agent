"""
profile.py — Nitish's confirmed financial profile (hardcoded, never committed).

Single source of truth for all financial calculations in INMarket.
Update this file locally after any financial change; it is gitignored on Mac.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FinancialProfile:
    # ── Identity ─────────────────────────────────────────────────────────────
    name: str = "Nitish Bidwe"
    age: int = 36
    location: str = "Ingolstadt, Germany"
    family: str = "Married, 1 child — sole earner"

    # ── Income ───────────────────────────────────────────────────────────────
    net_monthly: float = 4315.34          # after tax/SV
    kindergeld_monthly: float = 259.00    # Kindergeld + Familiengeld combined
    gross_annual: float = 75_000.00

    # ── Expenses (approximate — unlisted expenses likely exist) ───────────────
    rent: float = 1200.00
    groceries: float = 400.00
    electricity_internet: float = 100.00
    miscellaneous: float = 200.00

    @property
    def monthly_expenses(self) -> float:
        return self.rent + self.groceries + self.electricity_internet + self.miscellaneous

    @property
    def monthly_income_total(self) -> float:
        return self.net_monthly + self.kindergeld_monthly

    @property
    def monthly_surplus(self) -> float:
        return self.monthly_income_total - self.monthly_expenses

    # ── Savings ──────────────────────────────────────────────────────────────
    revolut_balance: float = 20_416.91    # @ 2.00% p.a.
    revolut_rate_pct: float = 2.00
    tagesgeld_balance: float = 50_000.00  # Scalable Capital — EMERGENCY BUFFER, LOCKED
    tagesgeld_rate_pct: float = 2.50

    @property
    def total_savings(self) -> float:
        return self.revolut_balance + self.tagesgeld_balance

    @property
    def emergency_buffer(self) -> float:
        return self.tagesgeld_balance  # NEVER invest this

    # ── Investments ──────────────────────────────────────────────────────────
    etf_invested: float = 0.00            # not yet started
    etf_plan_monthly: float = 500.00      # planned: VWCE.DE on Trade Republic

    # ── FIRE ─────────────────────────────────────────────────────────────────
    fire_target: float = 600_000.00       # 4% rule × ~€24K annual expenses × 25
    fire_annual_spend: float = 24_000.00

    # ── Tax (Germany) ────────────────────────────────────────────────────────
    steuerklasse: str = "III"
    sparer_pauschbetrag: float = 2_000.00  # married couple, joint — NOT €1,000
    steuererklarung_2024: str = "FILED ✅"
    steuererklarung_2025: str = "FILED ✅"
    freistellungsauftrag_scalable: str = "NOT YET FILED"  # action needed!
    vorabpauschale_next: str = "January 2026"

    # ── ETF Universe (allowed instruments only) ──────────────────────────────
    etf_universe: dict = field(default_factory=lambda: {
        "VWCE.DE":  {"name": "Vanguard FTSE All-World Acc",    "role": "Core global (primary)"},
        "IWDA.AS":  {"name": "iShares MSCI World Acc",         "role": "Developed markets"},
        "IS3N.DE":  {"name": "iShares MSCI EM Acc",            "role": "Emerging markets"},
        "IEAG.DE":  {"name": "iShares EUR Aggregate Bond",     "role": "Bond allocation"},
        "IWDP.DE":  {"name": "iShares Developed Property",     "role": "Real estate"},
    })

    # ── German tax constants ──────────────────────────────────────────────────
    abgeltungsteuer_rate: float = 0.26375  # 25% + 5.5% Soli
    basiszins_2025: float = 0.025          # for Vorabpauschale calc

    def months_of_expenses_covered(self) -> int:
        if self.monthly_expenses <= 0:
            return 0
        return int(self.emergency_buffer / self.monthly_expenses)

    def freistellung_interest_annual(self) -> float:
        """Annual interest on Tagesgeld at current rate."""
        return self.tagesgeld_balance * self.tagesgeld_rate_pct / 100

    def freistellung_tax_saving(self) -> float:
        """Tax saved by filing Freistellungsauftrag (up to Sparer-Pauschbetrag)."""
        taxable = min(self.freistellung_interest_annual(), self.sparer_pauschbetrag)
        return taxable * self.abgeltungsteuer_rate


# Singleton instance — import this throughout the app
PROFILE = FinancialProfile()
