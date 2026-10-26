"""
risk.py — Portfolio risk analysis for Nitish's ETF positions.

Calculates volatility, drawdown, Sharpe ratio, and diversification score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional
from core.market_data import get_history


@dataclass
class RiskMetrics:
    ticker: str
    annualised_return: float       # % p.a.
    annualised_volatility: float   # % p.a.
    sharpe_ratio: float            # (return - risk_free) / volatility
    max_drawdown: float            # worst peak-to-trough drop (%)
    current_dip_from_high: float   # % below 52-week high
    risk_level: str                # "LOW" | "MEDIUM" | "HIGH"
    verdict: str                   # short human-readable summary


RISK_FREE_RATE = 0.025  # ECB rate approximately, Oct 2026


def compute_risk(ticker: str, period: str = "1y") -> Optional[RiskMetrics]:
    """Compute risk metrics for a single ETF from historical data."""
    history = get_history(ticker, period)
    if history is None or len(history.closes) < 30:
        return None

    prices = history.closes

    # Daily returns
    returns = [
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(1, len(prices))
        if prices[i - 1] > 0
    ]
    if not returns:
        return None

    # Annualised return
    n = len(prices)
    total_return = (prices[-1] / prices[0]) - 1 if prices[0] > 0 else 0
    annualised_return = (1 + total_return) ** (252 / n) - 1

    # Annualised volatility
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    daily_std = math.sqrt(variance)
    annualised_vol = daily_std * math.sqrt(252)

    # Sharpe ratio
    sharpe = ((annualised_return - RISK_FREE_RATE) / annualised_vol) if annualised_vol > 0 else 0

    # Max drawdown
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        dd = (peak - price) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Current dip from 52-week high
    high_52w = max(prices)
    current_dip = (high_52w - prices[-1]) / high_52w * 100 if high_52w > 0 else 0

    # Risk classification
    if annualised_vol < 0.10:
        risk_level = "LOW"
    elif annualised_vol < 0.18:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    # Human verdict
    if sharpe > 0.8:
        verdict = f"Strong risk-adjusted return (Sharpe {sharpe:.2f})"
    elif sharpe > 0.4:
        verdict = f"Decent risk-adjusted return (Sharpe {sharpe:.2f})"
    else:
        verdict = f"Weak risk-adjusted return (Sharpe {sharpe:.2f}) — consider alternatives"

    return RiskMetrics(
        ticker=ticker,
        annualised_return=round(annualised_return * 100, 2),
        annualised_volatility=round(annualised_vol * 100, 2),
        sharpe_ratio=round(sharpe, 2),
        max_drawdown=round(max_dd * 100, 2),
        current_dip_from_high=round(current_dip, 2),
        risk_level=risk_level,
        verdict=verdict,
    )


def analyse_portfolio_risk(tickers: list[str]) -> dict[str, Optional[RiskMetrics]]:
    """Analyse risk for all tickers in a list."""
    return {ticker: compute_risk(ticker) for ticker in tickers}
