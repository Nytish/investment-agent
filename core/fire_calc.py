"""
fire_calc.py — FIRE projection engine with Monte Carlo simulation.

Calculates realistic wealth accumulation scenarios for Nitish's financial goals.
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Optional
from core.profile import PROFILE


@dataclass
class FireScenario:
    monthly_investment: float
    label: str
    p10: list[float] = field(default_factory=list)   # pessimistic
    p25: list[float] = field(default_factory=list)
    p50: list[float] = field(default_factory=list)   # median
    p75: list[float] = field(default_factory=list)
    p90: list[float] = field(default_factory=list)   # optimistic
    ages: list[int] = field(default_factory=list)
    fire_probability_by_47: float = 0.0              # % reaching €600K by age 47
    median_fire_age: Optional[int] = None            # age when P50 crosses €600K


def run_fire_projection(
    monthly_investment: float,
    initial_invested: float = 0.0,
    fire_target: float = PROFILE.fire_target,
    current_age: int = PROFILE.age,
    years: int = 35,
    simulations: int = 1000,
    mean_return: float = 0.07,   # 7% p.a. long-term equity average
    std_return: float = 0.15,    # 15% annualised volatility
    seed: int = 42,
) -> FireScenario:
    """
    Run Monte Carlo simulation of portfolio growth.

    Returns percentile bands and FIRE statistics.
    """
    rng = random.Random(seed)
    monthly_mean = (1 + mean_return) ** (1 / 12) - 1
    monthly_std = std_return / math.sqrt(12)

    n_months = years * 12
    all_paths: list[list[float]] = []

    for _ in range(simulations):
        portfolio = initial_invested
        path = [portfolio]
        for _ in range(n_months):
            monthly_return = rng.gauss(monthly_mean, monthly_std)
            portfolio = portfolio * (1 + monthly_return) + monthly_investment
            portfolio = max(portfolio, 0.0)  # no negative portfolio
            path.append(portfolio)
        all_paths.append(path)

    # Annual snapshots (every 12 months)
    yearly_paths = [[path[m * 12] for m in range(years + 1)] for path in all_paths]
    ages = [current_age + y for y in range(years + 1)]

    # Compute percentiles at each year
    def pct(year_idx: int, p: float) -> float:
        vals = sorted(path[year_idx] for path in yearly_paths)
        idx = int(p * (len(vals) - 1))
        return round(vals[idx], 2)

    scenario = FireScenario(
        monthly_investment=monthly_investment,
        label=f"€{monthly_investment:,.0f}/month",
        ages=ages,
    )

    for y in range(years + 1):
        scenario.p10.append(pct(y, 0.10))
        scenario.p25.append(pct(y, 0.25))
        scenario.p50.append(pct(y, 0.50))
        scenario.p75.append(pct(y, 0.75))
        scenario.p90.append(pct(y, 0.90))

    # FIRE probability by age 47
    years_to_47 = 47 - current_age
    if years_to_47 <= years and years_to_47 >= 0:
        idx_47 = years_to_47
        paths_at_47 = [path[idx_47] for path in yearly_paths]
        scenario.fire_probability_by_47 = sum(
            1 for v in paths_at_47 if v >= fire_target
        ) / simulations * 100

    # Median FIRE age (first year where P50 >= target)
    for i, (age, p50_val) in enumerate(zip(ages, scenario.p50)):
        if p50_val >= fire_target:
            scenario.median_fire_age = age
            break

    return scenario


def run_all_scenarios() -> list[FireScenario]:
    """Run three investment scenarios for comparison."""
    scenarios = [
        (300, "Conservative (€300/mo)"),
        (500, "Planned (€500/mo)"),
        (1000, "Accelerated (€1,000/mo)"),
    ]
    return [
        run_fire_projection(amount, label=label)
        for amount, label in scenarios
    ]


def fire_summary_text(scenario: FireScenario) -> str:
    """Short text summary of a FIRE scenario for the AI."""
    p50_now = scenario.p50[0]
    p50_10y = scenario.p50[min(10, len(scenario.p50) - 1)]
    fire_prob = scenario.fire_probability_by_47
    fire_age = scenario.median_fire_age or ">86"

    return (
        f"At {scenario.label}: "
        f"€{p50_10y:,.0f} median portfolio in 10 years. "
        f"FIRE probability by age 47: {fire_prob:.1f}%. "
        f"Median FIRE age: {fire_age}."
    )
