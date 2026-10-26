"""
market_data.py — Live ETF price data via yfinance.

Fetches real-time prices for Nitish's approved ETF universe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

ETF_TICKERS = {
    "VWCE": "VWCE.DE",
    "IWDA": "IWDA.AS",
    "IS3N": "IS3N.DE",
    "IEAG": "IEAG.DE",
    "IWDP": "IWDP.DE",
}

ETF_INFO = {
    "VWCE.DE": {"name": "Vanguard FTSE All-World Acc", "currency": "EUR", "role": "Core global"},
    "IWDA.AS": {"name": "iShares MSCI World Acc", "currency": "EUR", "role": "Developed markets"},
    "IS3N.DE": {"name": "iShares MSCI EM Acc", "currency": "EUR", "role": "Emerging markets"},
    "IEAG.DE": {"name": "iShares EUR Aggregate Bond", "currency": "EUR", "role": "Bonds"},
    "IWDP.DE": {"name": "iShares Developed Property", "currency": "EUR", "role": "Real estate"},
}


@dataclass
class ETFQuote:
    ticker: str
    name: str
    price: float
    prev_close: float
    change_pct: float
    day_high: float
    day_low: float
    week52_high: float
    week52_low: float
    volume: int
    currency: str
    timestamp: datetime
    role: str

    @property
    def change_eur(self) -> float:
        return self.price - self.prev_close

    @property
    def is_dip(self) -> bool:
        """Price more than 2% below 52-week high — potential buy opportunity."""
        if self.week52_high <= 0:
            return False
        return (self.week52_high - self.price) / self.week52_high > 0.02

    @property
    def dip_pct_from_high(self) -> float:
        """How far below 52-week high (as positive %)."""
        if self.week52_high <= 0:
            return 0.0
        return (self.week52_high - self.price) / self.week52_high * 100


@dataclass
class ETFHistory:
    ticker: str
    dates: list[str]
    closes: list[float]
    volumes: list[int]
    period: str


def get_quote(ticker: str) -> Optional[ETFQuote]:
    """Fetch live quote for a single ETF ticker."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="2d")

        if hist.empty or len(hist) < 1:
            return None

        price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

        etf_meta = ETF_INFO.get(ticker, {})
        name = etf_meta.get("name", info.get("longName", ticker))
        currency = etf_meta.get("currency", info.get("currency", "EUR"))
        role = etf_meta.get("role", "")

        return ETFQuote(
            ticker=ticker,
            name=name,
            price=price,
            prev_close=prev_close,
            change_pct=change_pct,
            day_high=float(hist["High"].iloc[-1]),
            day_low=float(hist["Low"].iloc[-1]),
            week52_high=float(info.get("fiftyTwoWeekHigh", hist["Close"].max())),
            week52_low=float(info.get("fiftyTwoWeekLow", hist["Close"].min())),
            volume=int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0,
            currency=currency,
            timestamp=datetime.now(),
            role=role,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch quote for {ticker}: {e}")
        return None


def get_all_quotes() -> dict[str, Optional[ETFQuote]]:
    """Fetch live quotes for all ETFs in the universe."""
    return {ticker: get_quote(ticker) for ticker in ETF_TICKERS.values()}


def get_history(ticker: str, period: str = "1y") -> Optional[ETFHistory]:
    """Fetch price history for charting."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return None
        return ETFHistory(
            ticker=ticker,
            dates=[d.strftime("%Y-%m-%d") for d in hist.index],
            closes=[round(float(c), 2) for c in hist["Close"]],
            volumes=[int(v) for v in hist["Volume"]] if "Volume" in hist.columns else [],
            period=period,
        )
    except Exception as e:
        logger.warning(f"History fetch failed for {ticker}: {e}")
        return None


def build_market_summary(quotes: dict) -> str:
    """Build a text summary of current market for the AI system prompt."""
    lines = ["Live ETF Prices:"]
    for ticker, quote in quotes.items():
        if quote:
            arrow = "↑" if quote.change_pct >= 0 else "↓"
            lines.append(
                f"  {ticker}: €{quote.price:.2f} {arrow}{abs(quote.change_pct):.2f}%"
                + (f" [DIP: {quote.dip_pct_from_high:.1f}% below 52wk high]" if quote.is_dip else "")
            )
        else:
            lines.append(f"  {ticker}: unavailable")
    return "\n".join(lines)
