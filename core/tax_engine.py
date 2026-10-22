"""
core/tax_engine.py — APEX 2.0
German investment tax calculations.

Covers:
  - Vorabpauschale (§18 InvStG) — annual prepayment tax on unrealised gains
  - Realisation tax — Abgeltungsteuer on selling ETF units
  - Freistellungsauftrag (FSA) tracking
  - Teilfreistellung — 30% exemption for equity ETFs

All arithmetic uses Decimal. No float.

References:
  §18 InvStG (Vorabpauschale)
  §20 EStG (Abgeltungsteuer 25% + §3 SolzG 5.5% Soli = 26.375%)
  §20 InvStG (Teilfreistellung — 30% exempt for equity funds)
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# ── Constants ────────────────────────────────────────────────────────────────
ABGELTUNGSTEUER_RATE = Decimal("0.26375")  # 25% KESt + 5.5% Soli
TEILFREISTELLUNG_EQUITY = Decimal("0.70")  # equity ETFs: 70% taxable, 30% exempt
BASISZINS_FACTOR = Decimal("0.70")         # §18(1) InvStG: base_return × 0.7
ZERO = Decimal("0")
CENT = Decimal("0.01")

# Real Bundesbank Basiszins by year (for offline use / tests).
# Source: https://api.bundesbank.de/service/data/BBK01/BBK01.SU0202
# Update each January when Bundesbank publishes the new rate.
KNOWN_BASISZINS: dict[int, Decimal] = {
    2022: Decimal("0.0012"),   # 0.12%
    2023: Decimal("0.0255"),   # 2.55%
    2024: Decimal("0.0229"),   # 2.29%
}


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class VorabpauschaleResult:
    """
    Result of the annual Vorabpauschale calculation for one fund position.

    Attributes
    ----------
    year            : Tax year.
    basiszins       : Bundesbank base rate for the year (e.g. Decimal("0.0229")).
    fund_value      : Fund value at start of year (€).
    price_gain      : max(0, fund_value_end − fund_value_start). Zero when fund fell.
    base_return     : fund_value × basiszins × 0.70 — theoretical return per §18.
    taxable_base    : min(base_return, price_gain) × Teilfreistellung.
    fsa_applied     : Portion of FSA consumed by this event.
    fsa_remaining_after : FSA balance after this event.
    tax_due         : Actual Abgeltungsteuer owed after FSA.
    """
    year: int
    basiszins: Decimal
    fund_value: Decimal
    price_gain: Decimal
    base_return: Decimal
    taxable_base: Decimal
    fsa_applied: Decimal
    fsa_remaining_after: Decimal
    tax_due: Decimal


@dataclass
class RealisationResult:
    """
    Result of capital-gains tax calculation on selling ETF units.

    Attributes
    ----------
    gain            : Raw gain before Teilfreistellung (€).
    taxable_gain    : gain × Teilfreistellung.
    fsa_applied     : Portion of FSA consumed.
    fsa_remaining_after : FSA balance after this event.
    tax_due         : Abgeltungsteuer owed after FSA.
    """
    gain: Decimal
    taxable_gain: Decimal
    fsa_applied: Decimal
    fsa_remaining_after: Decimal
    tax_due: Decimal


# ── Core calculations ─────────────────────────────────────────────────────────

def calculate_vorabpauschale(
    year: int,
    fund_value_start: Decimal,
    fund_value_end: Decimal,
    basiszins: Decimal,
    fsa_remaining: Decimal,
    is_equity_fund: bool = True,
) -> VorabpauschaleResult:
    """
    Calculate Vorabpauschale for one fund position for one year.

    Key rules:
    - Only applies when fund value increased (price_gain > 0).
    - base_return is capped at actual price gain — you cannot be taxed on
      more than the fund actually earned.
    - 30% Teilfreistellung for equity ETFs → only 70% of the amount is taxable.
    - FSA offsets taxable amount before applying the 26.375% rate.

    Parameters
    ----------
    fund_value_start : Fund NAV at 1 January of the tax year.
    fund_value_end   : Fund NAV at 31 December of the tax year.
    basiszins        : Bundesbank Basiszins for the year (e.g. Decimal("0.0229")).
    fsa_remaining    : Freistellungsauftrag balance at start of this calculation.
    is_equity_fund   : True for equity ETFs (VWCE, IWDA, etc.); False for bonds.
    """
    teilfreistellung = TEILFREISTELLUNG_EQUITY if is_equity_fund else Decimal("1")

    price_gain = max(ZERO, fund_value_end - fund_value_start)
    base_return = (fund_value_start * basiszins * BASISZINS_FACTOR).quantize(
        CENT, rounding=ROUND_HALF_UP
    )

    # Vorabpauschale gross = the lesser of the theoretical return and the actual gain.
    vorabpauschale_gross = min(base_return, price_gain)

    # Apply Teilfreistellung.
    taxable_base = (vorabpauschale_gross * teilfreistellung).quantize(
        CENT, rounding=ROUND_HALF_UP
    )

    # Apply FSA.
    fsa_applied = min(fsa_remaining, taxable_base)
    after_fsa = taxable_base - fsa_applied
    fsa_remaining_after = fsa_remaining - fsa_applied

    tax_due = (after_fsa * ABGELTUNGSTEUER_RATE).quantize(CENT, rounding=ROUND_HALF_UP)

    return VorabpauschaleResult(
        year=year,
        basiszins=basiszins,
        fund_value=fund_value_start,
        price_gain=price_gain,
        base_return=base_return,
        taxable_base=taxable_base,
        fsa_applied=fsa_applied,
        fsa_remaining_after=fsa_remaining_after,
        tax_due=tax_due,
    )


def calculate_realisation_tax(
    buy_price: Decimal,
    sell_price: Decimal,
    units: Decimal,
    fsa_remaining: Decimal,
    is_equity_fund: bool = True,
) -> RealisationResult:
    """
    Calculate Abgeltungsteuer on selling ETF units.

    Loss sales (sell_price < buy_price) produce negative taxable_gain.
    Losses do not consume FSA and result in tax_due = €0.
    (Loss offset rules across brokers require a Verlustverrechnungstopf — not modelled here.)
    """
    teilfreistellung = TEILFREISTELLUNG_EQUITY if is_equity_fund else Decimal("1")

    gain = (sell_price - buy_price) * units
    taxable_gain = (gain * teilfreistellung).quantize(CENT, rounding=ROUND_HALF_UP)

    # FSA only offsets positive gains.
    fsa_applied = min(fsa_remaining, max(ZERO, taxable_gain))
    after_fsa = max(ZERO, taxable_gain - fsa_applied)
    fsa_remaining_after = fsa_remaining - fsa_applied

    tax_due = (after_fsa * ABGELTUNGSTEUER_RATE).quantize(CENT, rounding=ROUND_HALF_UP)

    return RealisationResult(
        gain=gain,
        taxable_gain=taxable_gain,
        fsa_applied=fsa_applied,
        fsa_remaining_after=fsa_remaining_after,
        tax_due=tax_due,
    )


def annual_fsa_summary(
    vorabpauschale_results: list[VorabpauschaleResult],
    realisation_results: list[RealisationResult],
    fsa_total: Decimal = Decimal("2000"),  # €2,000 for married / Steuerklasse III
) -> dict:
    """
    Aggregate FSA usage and tax saved across all events in a calendar year.

    Returns
    -------
    dict with keys:
        fsa_total        : Annual allowance.
        fsa_used         : Total FSA consumed across all events.
        fsa_remaining    : Allowance not yet used.
        tax_saved        : Tax avoided by applying FSA (fsa_used × 26.375%).
        total_tax_due    : Actual tax owed after FSA.
    """
    vp_fsa = sum((r.fsa_applied for r in vorabpauschale_results), ZERO)
    re_fsa = sum((r.fsa_applied for r in realisation_results), ZERO)
    total_fsa_used = (vp_fsa + re_fsa).quantize(CENT, rounding=ROUND_HALF_UP)

    fsa_remaining = (fsa_total - total_fsa_used).quantize(CENT, rounding=ROUND_HALF_UP)
    tax_saved = (total_fsa_used * ABGELTUNGSTEUER_RATE).quantize(CENT, rounding=ROUND_HALF_UP)

    vp_tax = sum((r.tax_due for r in vorabpauschale_results), ZERO)
    re_tax = sum((r.tax_due for r in realisation_results), ZERO)
    total_tax_due = (vp_tax + re_tax).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "fsa_total": fsa_total,
        "fsa_used": total_fsa_used,
        "fsa_remaining": fsa_remaining,
        "tax_saved": tax_saved,
        "total_tax_due": total_tax_due,
    }
