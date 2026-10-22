"""
monte_carlo.py — APEX 2.0
1,000-simulation Monte Carlo portfolio projector.
Box-Muller normal sampling, no numpy dependency.
All portfolio values are Decimal; float is used only inside Box-Muller math.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_SIMULATIONS: int = 1_000
DEFAULT_FIRE_TARGET: Decimal = Decimal("600000")
MAX_MONTHS: int = 600   # 50-year horizon ceiling


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    monthly_investment: Decimal         # investable surplus per month
    initial_invested: Decimal           # existing portfolio value (€0 for Nitish now)
    annual_return_mean: float = 0.07    # 7% long-run real return (global equity ETF)
    annual_return_std: float = 0.15     # 15% annual std dev — realistic for equity
    years: int = 11                     # 36 → 47
    simulations: int = DEFAULT_SIMULATIONS
    fire_target: Decimal = field(default_factory=lambda: DEFAULT_FIRE_TARGET)


@dataclass
class MonteCarloResult:
    config: SimulationConfig
    # Percentile bands — list index is year (0 = start, 1 = end of year 1, …)
    p5:  list[Decimal]
    p25: list[Decimal]
    p50: list[Decimal]
    p75: list[Decimal]
    p95: list[Decimal]
    # FIRE metrics
    fire_probability: Decimal           # fraction of sims reaching fire_target by final year
    median_fire_age: int | None         # first age at which P50 >= fire_target (None if never)
    # Raw yearly snapshots — [sim_index][year_index], shape: sims × (years+1)
    yearly_snapshots: list[list[Decimal]]


# ── Private helpers ───────────────────────────────────────────────────────────

def _box_muller(mu: float, sigma: float) -> float:
    """Box-Muller transform: two uniform samples → one normal variate."""
    while True:
        u1 = random.random()
        u2 = random.random()
        if u1 > 0:   # guard against log(0)
            break
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def _percentile(values: list[float], pct: float) -> Decimal:
    """Linear-interpolation percentile (no numpy). Returns Decimal rounded to cents."""
    if not values:
        return Decimal("0.00")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = pct / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    interpolated = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
    return Decimal(str(round(interpolated, 2)))


def _dec(val: float) -> Decimal:
    """Round float to 2dp Decimal."""
    return Decimal(str(round(val, 2)))


# ── Core simulation ───────────────────────────────────────────────────────────

def run_simulation(config: SimulationConfig, seed: int = 42) -> MonteCarloResult:
    """
    Run `config.simulations` Monte Carlo paths and return percentile fan-chart data.

    Parameters
    ----------
    config : SimulationConfig
    seed   : int — random seed for reproducibility (tests use seed=42)

    Returns
    -------
    MonteCarloResult with P5/P25/P50/P75/P95 bands and FIRE probability.
    """
    random.seed(seed)

    monthly_rate_mean = (1.0 + config.annual_return_mean) ** (1.0 / 12.0) - 1.0
    monthly_rate_std  = config.annual_return_std / math.sqrt(12.0)

    monthly_invest = float(config.monthly_investment)
    initial        = float(config.initial_invested)
    n_months       = config.years * 12
    fire_target_f  = float(config.fire_target)

    all_paths: list[list[float]] = []

    for _ in range(config.simulations):
        portfolio = initial
        path: list[float] = [portfolio]    # year 0
        for month in range(1, n_months + 1):
            r = _box_muller(monthly_rate_mean, monthly_rate_std)
            portfolio = portfolio * (1.0 + r) + monthly_invest
            if portfolio < 0.0:            # floor at zero — no negative portfolio
                portfolio = 0.0
            if month % 12 == 0:
                path.append(portfolio)
        all_paths.append(path)

    # ── Percentile bands by year ─────────────────────────────────────────────
    n_years = config.years + 1    # includes year 0
    p5_band:  list[Decimal] = []
    p25_band: list[Decimal] = []
    p50_band: list[Decimal] = []
    p75_band: list[Decimal] = []
    p95_band: list[Decimal] = []

    for yr in range(n_years):
        year_vals = [path[yr] for path in all_paths]
        p5_band.append(_percentile(year_vals, 5))
        p25_band.append(_percentile(year_vals, 25))
        p50_band.append(_percentile(year_vals, 50))
        p75_band.append(_percentile(year_vals, 75))
        p95_band.append(_percentile(year_vals, 95))

    # ── FIRE probability ─────────────────────────────────────────────────────
    fire_count = sum(1 for path in all_paths if path[-1] >= fire_target_f)
    fire_probability = _dec(fire_count / config.simulations).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    # ── Median FIRE age ──────────────────────────────────────────────────────
    # Find first year index where P50 >= fire_target
    fire_age_start = 36    # Nitish's current age; could be extracted from config later
    median_fire_age: int | None = None
    for yr_idx, p50_val in enumerate(p50_band):
        if p50_val >= config.fire_target:
            median_fire_age = fire_age_start + yr_idx
            break

    # ── Convert raw paths to Decimal snapshots ───────────────────────────────
    yearly_snapshots: list[list[Decimal]] = [
        [_dec(v) for v in path] for path in all_paths
    ]

    return MonteCarloResult(
        config=config,
        p5=p5_band,
        p25=p25_band,
        p50=p50_band,
        p75=p75_band,
        p95=p95_band,
        fire_probability=fire_probability,
        median_fire_age=median_fire_age,
        yearly_snapshots=yearly_snapshots,
    )


# ── Convenience: find required monthly investment for P50 FIRE by target age ──

def monthly_needed_for_fire_by_age(
    fire_target: Decimal,
    initial_invested: Decimal,
    target_age: int,
    current_age: int,
    annual_return_mean: float = 0.07,
    seed: int = 42,
) -> Decimal:
    """
    Binary-search the monthly investment amount needed so P50 reaches
    `fire_target` exactly by `target_age`. Returns -1 if impossible.
    """
    years = target_age - current_age
    if years <= 0:
        return Decimal("-1")

    lo, hi = 0.0, float(fire_target)   # wide search range
    for _ in range(40):                  # 40 iterations → ±€1 precision
        mid = (lo + hi) / 2.0
        cfg = SimulationConfig(
            monthly_investment=_dec(mid),
            initial_invested=initial_invested,
            annual_return_mean=annual_return_mean,
            years=years,
            simulations=500,             # faster for search
            fire_target=fire_target,
        )
        result = run_simulation(cfg, seed=seed)
        if result.p50[-1] < fire_target:
            lo = mid
        else:
            hi = mid

    monthly = _dec((lo + hi) / 2.0)
    # Sanity: if answer is unrealistically large (>€50K/month), return -1
    if monthly > Decimal("50000"):
        return Decimal("-1")
    return monthly
