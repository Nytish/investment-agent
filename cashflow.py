"""
cashflow.py — APEX 2.0
Deterministic cash-flow calculations using decimal-safe arithmetic.
No LLM calls. No network access. No external dependencies beyond stdlib + PyYAML.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional
import datetime
import yaml


CENTS = Decimal("0.01")


def _d(value) -> Decimal:
    """Convert any numeric input to a Decimal, rounded to 2 dp."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass
class IncomeResult:
    net_monthly: Decimal
    kindergeld: Decimal
    total_monthly: Decimal
    verification_status: str
    employment_risk: str


@dataclass
class ExpenseResult:
    rent: Decimal
    groceries: Decimal
    electricity_internet: Decimal
    miscellaneous: Decimal
    total_listed: Decimal
    unlisted_warning: bool
    verification_status: str


@dataclass
class SurplusResult:
    gross_surplus: Decimal          # income minus listed expenses only
    verification_status: str        # always UNVERIFIED until expenses confirmed
    warnings: list[str] = field(default_factory=list)


@dataclass
class SavingsResult:
    revolut_balance: Decimal
    revolut_rate: Decimal
    scalable_balance: Decimal
    scalable_rate: Decimal
    total_savings: Decimal
    verification_status: str


def load_profile(profile_path: Path) -> dict:
    with open(profile_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def calculate_income(profile: dict) -> IncomeResult:
    inc = profile["income"]
    net = _d(inc["net_monthly"])
    kindergeld = _d(inc.get("kindergeld_monthly", 0))
    return IncomeResult(
        net_monthly=net,
        kindergeld=kindergeld,
        total_monthly=net + kindergeld,
        verification_status=inc.get("verification_status", "UNVERIFIED"),
        employment_risk=inc.get("employment_risk", "Unknown"),
    )


def calculate_expenses(profile: dict) -> ExpenseResult:
    exp = profile["expenses"]
    rent = _d(exp["rent"])
    groceries = _d(exp["groceries"])
    elec = _d(exp["electricity_internet"])
    misc = _d(exp["miscellaneous"])
    total = rent + groceries + elec + misc
    return ExpenseResult(
        rent=rent,
        groceries=groceries,
        electricity_internet=elec,
        miscellaneous=misc,
        total_listed=total,
        unlisted_warning=bool(exp.get("unlisted_expense_warning", True)),
        verification_status=exp.get("verification_status", "UNVERIFIED"),
    )


def calculate_surplus(income: IncomeResult, expenses: ExpenseResult) -> SurplusResult:
    gross = income.net_monthly - expenses.total_listed
    warnings = []
    if expenses.unlisted_warning:
        warnings.append(
            "UNVERIFIED SURPLUS: Listed expenses are likely incomplete. "
            "Insurance, phone, transport, childcare and subscriptions are "
            "not included. Review 3 months of bank statements before "
            "treating this surplus as investable."
        )
    if income.verification_status != "VERIFIED":
        warnings.append(
            f"Income not verified from payslip: {income.verification_status}"
        )
    status = "UNVERIFIED" if warnings else "VERIFIED"
    return SurplusResult(
        gross_surplus=gross,
        verification_status=status,
        warnings=warnings,
    )


def calculate_savings(profile: dict) -> SavingsResult:
    sav = profile["savings"]
    rev = _d(sav["revolut_instant"]["balance"])
    rev_rate = _d(sav["revolut_instant"]["rate_pct"])
    scal = _d(sav["scalable_capital_tagesgeld"]["balance"])
    scal_rate = _d(sav["scalable_capital_tagesgeld"]["rate_pct"])
    total = rev + scal
    return SavingsResult(
        revolut_balance=rev,
        revolut_rate=rev_rate,
        scalable_balance=scal,
        scalable_rate=scal_rate,
        total_savings=total,
        verification_status=sav.get("verification_status", "UNVERIFIED"),
    )


def estimate_annual_interest(savings: SavingsResult) -> Decimal:
    """Estimate gross annual interest across all savings accounts."""
    revolut_interest = (savings.revolut_balance * savings.revolut_rate / _d("100")).quantize(CENTS)
    scalable_interest = (savings.scalable_balance * savings.scalable_rate / _d("100")).quantize(CENTS)
    return revolut_interest + scalable_interest


def months_of_expenses_covered(savings_total: Decimal, monthly_expenses: Decimal) -> Decimal:
    if monthly_expenses <= Decimal("0"):
        raise ValueError("Monthly expenses must be > 0")
    return (savings_total / monthly_expenses).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


if __name__ == "__main__":
    profile_path = Path(__file__).parent / "data" / "financial_profile.yaml"
    profile = load_profile(profile_path)
    income = calculate_income(profile)
    expenses = calculate_expenses(profile)
    surplus = calculate_surplus(income, expenses)
    savings = calculate_savings(profile)
    coverage = months_of_expenses_covered(savings.total_savings, expenses.total_listed)

    print(f"Net income:       €{income.net_monthly:>10}")
    print(f"Kindergeld:       €{income.kindergeld:>10}")
    print(f"Total income:     €{income.total_monthly:>10}")
    print(f"Listed expenses:  €{expenses.total_listed:>10}")
    print(f"Gross surplus:    €{surplus.gross_surplus:>10}  [{surplus.verification_status}]")
    print(f"Total savings:    €{savings.total_savings:>10}  [{savings.verification_status}]")
    print(f"Expense coverage: {coverage} months")
    if surplus.warnings:
        print("\n⚠ WARNINGS:")
        for w in surplus.warnings:
            print(f"  • {w}")
