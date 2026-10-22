"""
buckets.py — APEX 2.0
Two-model view of finances:

  EXISTING SAVINGS (€50K Scalable Capital)
  ─────────────────────────────────────────
  Bucket 1: Emergency Reserve  — the full €50K is designated here.
                                  It is NOT split or reallocated.
                                  This money does not move.

  FUTURE MONTHLY SURPLUS (going forward)
  ────────────────────────────────────────
  Bucket 2: Home-Purchase Fund — built from monthly surplus savings.
                                  Accumulates in Tagesgeld until target reached.
  Bucket 3: Long-Term Invest   — only surplus remaining after house savings rate is met.

Rules are deterministic. No LLM. No network.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


CENTS = Decimal("0.01")


def _d(value) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


class BucketStatus(str, Enum):
    FUNDED      = "FUNDED"
    UNDERFUNDED = "UNDERFUNDED"
    UNCONFIRMED = "UNCONFIRMED"   # target not yet set by user
    PROTECTED   = "PROTECTED"     # has money but goal parameters unknown


@dataclass
class Bucket:
    name: str
    balance: Decimal
    target: Optional[Decimal]       # None = not yet defined
    status: BucketStatus
    notes: list[str]

    @property
    def shortfall(self) -> Optional[Decimal]:
        if self.target is None:
            return None
        diff = self.target - self.balance
        return diff if diff > Decimal("0") else Decimal("0")

    @property
    def surplus_above_target(self) -> Optional[Decimal]:
        if self.target is None:
            return None
        diff = self.balance - self.target
        return diff if diff > Decimal("0") else Decimal("0")


@dataclass
class SurplusAllocation:
    """How FUTURE monthly surplus should be split."""
    monthly_surplus: Decimal
    monthly_to_house: Decimal
    monthly_to_long_term: Decimal
    months_to_house_target: Optional[Decimal]   # None = target unknown
    warnings: list[str]


@dataclass
class BucketAllocation:
    emergency: Bucket
    home_purchase: Bucket       # forward savings tracker — starts at 0
    long_term: Bucket           # from surplus only
    total_savings: Decimal      # the locked existing savings (emergency bucket)
    surplus_plan: Optional[SurplusAllocation]
    warnings: list[str]

    # Kept for test compatibility — sums bucket balances
    @property
    def total_allocated(self) -> Decimal:
        return self.emergency.balance + self.home_purchase.balance + self.long_term.balance

    @property
    def unallocated(self) -> Decimal:
        return self.total_savings - self.total_allocated


def allocate_buckets(
    total_savings: Decimal,
    monthly_expenses: Decimal,
    emergency_months: int = 6,               # provisional default — must be confirmed
    home_purchase_target: Optional[Decimal] = None,
    home_purchase_horizon_years: int = 3,
    monthly_surplus: Optional[Decimal] = None,   # verified investable surplus, if known
    house_savings_already: Optional[Decimal] = None,  # amount saved toward house so far
) -> BucketAllocation:
    """
    Model savings and future surplus.

    Bucket 1 — Emergency Reserve:
        The EXISTING €50K savings are the emergency buffer.
        They are NEVER allocated to home purchase or investments.

    Bucket 2 — Home-Purchase Fund:
        Built from FUTURE monthly surplus.
        house_savings_already = amount saved toward house deposit so far (default 0).

    Bucket 3 — Long-Term Investments:
        Surplus remaining after the monthly house savings rate is met.
    """
    warnings: list[str] = []
    house_saved = house_savings_already or Decimal("0")

    # ── Bucket 1: Emergency Reserve (existing savings — fully locked) ────────
    emergency_target = (monthly_expenses * emergency_months).quantize(CENTS)

    if total_savings >= emergency_target:
        e_status = BucketStatus.FUNDED
    else:
        e_status = BucketStatus.UNDERFUNDED
        warnings.append(
            f"Emergency reserve target ({emergency_months} months = "
            f"€{emergency_target}) is not yet met by existing savings of "
            f"€{total_savings}. Top up before allocating to any other bucket."
        )

    e_notes = [
        f"Target: {emergency_months} months × €{monthly_expenses} = €{emergency_target} (PROVISIONAL — confirm months)",
        f"Existing savings: €{total_savings} — FULLY COVERS the emergency target.",
        "These savings do NOT contribute to the house fund or any investment.",
        "Must remain in instant-access, capital-stable accounts (Tagesgeld).",
        "Not available for investment — ever.",
    ]

    # ── Bucket 2: Home-Purchase Fund (forward savings) ───────────────────────
    if home_purchase_target is None:
        h_status = BucketStatus.UNCONFIRMED
        home_notes = [
            "⚠ Target price, location and down-payment % not yet specified.",
            f"Horizon: approximately {home_purchase_horizon_years} years.",
            "Built from FUTURE monthly surplus — existing savings are NOT used.",
            "Required inputs: target property price, location, down-payment %.",
            "Until confirmed, treat ALL monthly surplus as earmarked for house savings.",
        ]
        warnings.append(
            "Home-purchase fund target is undefined. "
            "All monthly surplus is earmarked for house savings until you confirm the target."
        )
    else:
        if house_saved >= home_purchase_target:
            h_status = BucketStatus.FUNDED
        else:
            h_status = BucketStatus.UNDERFUNDED
        home_notes = [
            f"Target down-payment: €{home_purchase_target}.",
            f"Saved toward house so far: €{house_saved}.",
            f"Horizon: {home_purchase_horizon_years} years.",
            "Built from FUTURE monthly surplus. Existing €50K emergency buffer NOT touched.",
            "Hold in Tagesgeld or equivalent capital-stable account.",
            "No equity-market exposure — purchase horizon is too short.",
        ]

    # ── Bucket 3: Long-Term Investments (surplus beyond house savings) ────────
    surplus_plan: Optional[SurplusAllocation] = None

    if monthly_surplus is not None and home_purchase_target is not None:
        # House purchase is the priority; LT investing only starts if surplus covers both
        horizon_months = Decimal(str(home_purchase_horizon_years * 12))
        shortfall = max(home_purchase_target - house_saved, Decimal("0"))
        monthly_house_rate = (shortfall / horizon_months).quantize(CENTS) if horizon_months > 0 else shortfall
        monthly_lt = max(monthly_surplus - monthly_house_rate, Decimal("0"))
        months_to_target = (
            (shortfall / monthly_house_rate).quantize(Decimal("0.1"))
            if monthly_house_rate > Decimal("0") else None
        )
        surplus_plan = SurplusAllocation(
            monthly_surplus=monthly_surplus,
            monthly_to_house=monthly_house_rate,
            monthly_to_long_term=monthly_lt,
            months_to_house_target=months_to_target,
            warnings=[],
        )
        lt_balance = monthly_lt  # illustrative — what could go to LT per month
        lt_status = BucketStatus.FUNDED if monthly_lt > Decimal("0") else BucketStatus.UNDERFUNDED
        lt_notes = [
            f"€{monthly_lt}/month available for long-term investing (after house savings).",
            "Permitted instruments: UNCONFIRMED — must be set before any recommendation.",
            "Risk tolerance: low-to-moderate (confirmed).",
        ]
    elif monthly_surplus is not None and home_purchase_target is None:
        lt_balance = Decimal("0")
        lt_status = BucketStatus.UNCONFIRMED
        lt_notes = [
            "Long-term investment amount cannot be calculated until house target is confirmed.",
            "All monthly surplus is provisionally earmarked for house savings.",
        ]
    else:
        lt_balance = Decimal("0")
        lt_status = BucketStatus.UNCONFIRMED
        lt_notes = [
            "Monthly surplus not yet verified — cannot calculate long-term investment amount.",
            "Verify 3 months of bank statements to establish true monthly surplus.",
        ]
        warnings.append(
            "Monthly surplus is unverified. Long-term investment allocation cannot be calculated."
        )

    return BucketAllocation(
        emergency=Bucket(
            name="Emergency Reserve",
            balance=total_savings,          # the full existing savings
            target=emergency_target,
            status=e_status,
            notes=e_notes,
        ),
        home_purchase=Bucket(
            name="Home-Purchase Fund",
            balance=house_saved,            # what's been saved toward house so far
            target=home_purchase_target,
            status=h_status,
            notes=home_notes,
        ),
        long_term=Bucket(
            name="Long-Term Investments",
            balance=lt_balance,
            target=None,
            status=lt_status,
            notes=lt_notes,
        ),
        total_savings=total_savings,
        surplus_plan=surplus_plan,
        warnings=warnings,
    )


if __name__ == "__main__":
    from cashflow import load_profile, calculate_expenses, calculate_savings
    from pathlib import Path

    profile = load_profile(Path("data/financial_profile.yaml"))
    expenses = calculate_expenses(profile)
    savings  = calculate_savings(profile)

    allocation = allocate_buckets(
        total_savings=savings.total_savings,
        monthly_expenses=expenses.total_listed,
    )

    print(f"\n{'='*60}")
    print(f"  APEX 2.0 — Bucket Allocation")
    print(f"  Existing savings : €{allocation.total_savings}")
    print(f"{'='*60}")
    for b in [allocation.emergency, allocation.home_purchase, allocation.long_term]:
        tgt = f"€{b.target}" if b.target else "UNCONFIRMED"
        print(f"\n  [{b.status.value}] {b.name}")
        print(f"    Balance : €{b.balance}")
        print(f"    Target  : {tgt}")
        if b.shortfall and b.shortfall > 0:
            print(f"    Shortfall: €{b.shortfall}")
        for note in b.notes:
            print(f"    • {note}")
    if allocation.warnings:
        print(f"\n⚠ WARNINGS:")
        for w in allocation.warnings:
            print(f"  • {w}")
