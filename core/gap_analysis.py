"""
gap_analysis.py — APEX 2.0
Home purchase and FIRE gap analysis engines.
All monetary values use Decimal (never float).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_UP, Decimal, getcontext

getcontext().prec = 28

_FOUR_RULE_MULTIPLIER = Decimal("25")  # 4% safe-withdrawal rule → 25× annual expenses


@dataclass
class HomeGapResult:
    target_price: Decimal
    down_payment_required: Decimal      # target_price × down_pct
    current_savings: Decimal
    monthly_surplus: Decimal
    months_to_target: int               # -1 if monthly_surplus == 0 and not covered
    years_to_target: Decimal            # months / 12 (0 if already covered)
    shortfall: Decimal                  # max(0, down_payment - savings)
    already_covered: bool


@dataclass
class FireGapResult:
    fire_target: Decimal                # annual_expenses × 25 (4% rule)
    current_invested: Decimal
    monthly_investment: Decimal
    assumed_annual_return: Decimal      # e.g. Decimal("0.07") for 7%
    years_to_fire: Decimal              # 999 if not reachable in 50 years
    fire_age: int                       # current_age + ceil(years_to_fire); 999 if unreachable
    monthly_needed_to_hit_age: int      # monthly investment needed to reach fire_target by target_fire_age


# ─────────────────────────────────────────────────────────────────────────────
# Home purchase gap
# ─────────────────────────────────────────────────────────────────────────────

def calculate_home_gap(
    target_price: Decimal,
    down_pct: Decimal,
    current_savings: Decimal,
    monthly_surplus: Decimal,
) -> HomeGapResult:
    """
    Calculate how far current savings are from a home purchase down payment,
    and how many months it takes to close the gap from monthly surplus.

    Args:
        target_price:    expected property purchase price
        down_pct:        down-payment fraction, e.g. Decimal("0.20")
        current_savings: savings available for down payment (NOT emergency buffer)
        monthly_surplus: investable surplus per month

    Returns:
        HomeGapResult with months_to_target == -1 if zero surplus and not covered.
    """
    down_payment_required = (target_price * down_pct).quantize(Decimal("0.01"))
    shortfall = max(Decimal("0"), down_payment_required - current_savings)
    already_covered = shortfall == Decimal("0")

    if already_covered:
        months_to_target = 0
        years_to_target = Decimal("0")
    elif monthly_surplus <= Decimal("0"):
        months_to_target = -1
        years_to_target = Decimal("999")
    else:
        # math.ceil on Decimal via float conversion — result is an integer, precision safe
        months_to_target = math.ceil(float(shortfall / monthly_surplus))
        years_to_target = (Decimal(str(months_to_target)) / Decimal("12")).quantize(
            Decimal("0.1")
        )

    return HomeGapResult(
        target_price=target_price,
        down_payment_required=down_payment_required,
        current_savings=current_savings,
        monthly_surplus=monthly_surplus,
        months_to_target=months_to_target,
        years_to_target=years_to_target,
        shortfall=shortfall,
        already_covered=already_covered,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FIRE gap
# ─────────────────────────────────────────────────────────────────────────────

def _monthly_rate_from_annual(annual_return: Decimal) -> Decimal:
    """Convert annual return to monthly rate as Decimal (float used once for root)."""
    # (1 + r_annual)^(1/12) - 1; float is used only for this one-time conversion
    return Decimal(str(math.pow(1.0 + float(annual_return), 1.0 / 12.0) - 1.0))


def _fv_after_n_months(
    pv: Decimal,
    monthly_pmt: Decimal,
    monthly_rate: Decimal,
    n: int,
) -> Decimal:
    """
    Future value of portfolio after n months.
    FV = PV*(1+r)^n + PMT * [((1+r)^n - 1) / r]
    All Decimal arithmetic.
    """
    if monthly_rate == Decimal("0"):
        return pv + monthly_pmt * Decimal(str(n))
    growth = (Decimal("1") + monthly_rate) ** n
    return pv * growth + monthly_pmt * ((growth - Decimal("1")) / monthly_rate)


def _monthly_needed_for_target(
    fire_target: Decimal,
    current_invested: Decimal,
    monthly_rate: Decimal,
    target_months: int,
) -> int:
    """
    Return the minimum monthly investment (rounded up to nearest euro) needed
    to reach fire_target in exactly target_months months.

    Uses the closed-form annuity formula:
        PMT = (FV - PV*(1+r)^n) * r / ((1+r)^n - 1)
    """
    if target_months <= 0:
        return 999_999

    growth = (Decimal("1") + monthly_rate) ** target_months
    fv_existing = current_invested * growth

    if fv_existing >= fire_target:
        return 0  # already on track without any new investment

    if monthly_rate == Decimal("0"):
        needed = (fire_target - fv_existing) / Decimal(str(target_months))
    else:
        needed = (fire_target - fv_existing) * monthly_rate / (growth - Decimal("1"))

    # Round up to the nearest whole euro
    return int(needed.to_integral_value(rounding=ROUND_UP))


def calculate_fire_gap(
    annual_expenses: Decimal,
    current_invested: Decimal,
    monthly_investment: Decimal,
    current_age: int,
    target_fire_age: int,
    assumed_annual_return: Decimal = Decimal("0.07"),
) -> FireGapResult:
    """
    Project when current_invested + monthly_investment reaches the FIRE target
    (25× annual expenses under the 4% rule).

    Args:
        annual_expenses:        current annual living expenses
        current_invested:       portfolio balance today (ETFs/investments; NOT emergency buffer)
        monthly_investment:     planned monthly investment contribution
        current_age:            age today
        target_fire_age:        desired retirement age
        assumed_annual_return:  long-run real return assumption (default 7%)

    Returns:
        FireGapResult; years_to_fire == 999 and fire_age == 999 if unreachable in 50 years.
    """
    fire_target = (annual_expenses * _FOUR_RULE_MULTIPLIER).quantize(Decimal("0.01"))
    monthly_rate = _monthly_rate_from_annual(assumed_annual_return)

    # Iterate month by month to find first month portfolio ≥ fire_target
    months_to_fire = -1
    for month in range(1, 601):  # max 50 years
        fv = _fv_after_n_months(current_invested, monthly_investment, monthly_rate, month)
        if fv >= fire_target:
            months_to_fire = month
            break

    if months_to_fire == -1:
        years_to_fire = Decimal("999")
        fire_age = 999
    else:
        years_to_fire = (Decimal(str(months_to_fire)) / Decimal("12")).quantize(
            Decimal("0.1")
        )
        fire_age = current_age + math.ceil(float(years_to_fire))

    # How much monthly investment is needed to hit target_fire_age?
    target_months = (target_fire_age - current_age) * 12
    monthly_needed = _monthly_needed_for_target(
        fire_target, current_invested, monthly_rate, target_months
    )

    return FireGapResult(
        fire_target=fire_target,
        current_invested=current_invested,
        monthly_investment=monthly_investment,
        assumed_annual_return=assumed_annual_return,
        years_to_fire=years_to_fire,
        fire_age=fire_age,
        monthly_needed_to_hit_age=monthly_needed,
    )
