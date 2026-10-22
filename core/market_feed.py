"""
market_feed.py — Layer 4 Market Intelligence
Provides ETF prices, Bundesbank Basiszins, and ECB deposit rate.

Data sources:
  - ETF prices:   yfinance (Yahoo Finance, unofficial) with SQLite cache fallback
  - Basiszins:    Bundesbank REST API (official, free, no key)
  - ECB rate:     ECB SDMX API (official, free, no key)

All monetary values use Decimal — no float arithmetic.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ETF_TICKERS: dict[str, str] = {
    "VWCE": "VWCE.DE",
    "IWDA": "IWDA.AS",
    "IS3N": "IS3N.DE",
    "IEAG": "IEAG.DE",
    "IWDP": "IWDP.DE",
}

# Bundesbank: BBK01.SU0202 = Basiszins (§247 BGB)
BUNDESBANK_URL = (
    "https://api.bundesbank.de/service/data/BBK01/BBK01.SU0202"
    "?detail=dataonly&startPeriod={year}-01-01&endPeriod={year}-12-31"
    "&format=json"
)

# ECB: deposit facility rate
ECB_URL = (
    "https://sdw-wsrest.ecb.europa.eu/service/data/"
    "FM/M.U2.EUR.RT0.MM.EURIBOR3MD_.HSTA"
    "?format=jsondata&lastNObservations=1"
)

CACHE_DB_PATH = Path(__file__).parent.parent / "data" / "market_cache.db"
CACHE_TTL_DAYS = 90
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0  # seconds


# ---------------------------------------------------------------------------
# SQLite cache
# ---------------------------------------------------------------------------

class MarketCache:
    """
    Persistent SQLite cache for ETF prices and rate data.
    Stores up to CACHE_TTL_DAYS days of history.
    Falls back to cached value if live fetch fails.
    """

    def __init__(self, db_path: Path = CACHE_DB_PATH) -> None:
        self._db = db_path
        self._db.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS etf_prices (
                    ticker      TEXT NOT NULL,
                    price_date  TEXT NOT NULL,
                    close_price TEXT NOT NULL,          -- stored as string to preserve Decimal
                    fetched_at  TEXT NOT NULL,
                    PRIMARY KEY (ticker, price_date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rates (
                    rate_key    TEXT NOT NULL,
                    period      TEXT NOT NULL,
                    value       TEXT NOT NULL,          -- stored as string
                    fetched_at  TEXT NOT NULL,
                    PRIMARY KEY (rate_key, period)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_etf_date
                ON etf_prices (ticker, price_date DESC)
            """)

    # --- ETF prices ---

    def get_price(self, ticker: str, for_date: date) -> Optional[Decimal]:
        """Return cached price for ticker on given date, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT close_price FROM etf_prices WHERE ticker=? AND price_date=?",
                (ticker, for_date.isoformat()),
            ).fetchone()
        if row:
            try:
                return Decimal(row["close_price"])
            except InvalidOperation:
                logger.warning("Corrupt cache entry for %s %s", ticker, for_date)
                return None
        return None

    def get_latest_price(self, ticker: str) -> Optional[tuple[date, Decimal]]:
        """Return most recent cached (date, price) for ticker, or None."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT price_date, close_price FROM etf_prices
                   WHERE ticker=? ORDER BY price_date DESC LIMIT 1""",
                (ticker,),
            ).fetchone()
        if row:
            try:
                return date.fromisoformat(row["price_date"]), Decimal(row["close_price"])
            except (InvalidOperation, ValueError):
                return None
        return None

    def put_price(self, ticker: str, for_date: date, price: Decimal) -> None:
        now = date.today().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO etf_prices
                   (ticker, price_date, close_price, fetched_at)
                   VALUES (?, ?, ?, ?)""",
                (ticker, for_date.isoformat(), str(price), now),
            )

    def purge_old(self) -> int:
        cutoff = (date.today() - timedelta(days=CACHE_TTL_DAYS)).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM etf_prices WHERE price_date < ?", (cutoff,)
            )
            return cur.rowcount

    # --- Rates ---

    def get_rate(self, rate_key: str, period: str) -> Optional[Decimal]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM rates WHERE rate_key=? AND period=?",
                (rate_key, period),
            ).fetchone()
        if row:
            try:
                return Decimal(row["value"])
            except InvalidOperation:
                return None
        return None

    def put_rate(self, rate_key: str, period: str, value: Decimal) -> None:
        now = date.today().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO rates
                   (rate_key, period, value, fetched_at)
                   VALUES (?, ?, ?, ?)""",
                (rate_key, period, str(value), now),
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _retry(fn, attempts: int = RETRY_ATTEMPTS, base_delay: float = RETRY_BASE_DELAY):
    """Call fn() up to `attempts` times with exponential back-off."""
    last_exc = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning("Attempt %d/%d failed (%s). Retrying in %.1fs…",
                               attempt + 1, attempts, exc, delay)
                time.sleep(delay)
    raise last_exc


def _requests_get(url: str, timeout: int = 15) -> dict:
    """Thin wrapper so tests can mock without patching requests directly."""
    import requests  # lazy import — not available in all test envs
    resp = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_cache = MarketCache()  # module-level singleton; replace in tests via monkeypatch


def fetch_etf_price(
    ticker: str,
    for_date: Optional[date] = None,
    *,
    cache: Optional[MarketCache] = None,
    use_cache: bool = True,
) -> Decimal:
    """
    Return latest closing price for ETF ticker as Decimal.

    ticker:    logical name, e.g. "VWCE"  (mapped via ETF_TICKERS)
    for_date:  if None, uses today / most recent trading day
    cache:     override module cache (useful in tests)
    use_cache: set False to force live fetch (still writes to cache)

    Raises ValueError for unknown tickers.
    Raises RuntimeError if both live fetch and cache fail.
    """
    if ticker not in ETF_TICKERS:
        raise ValueError(f"Unknown ticker '{ticker}'. Known: {list(ETF_TICKERS)}")

    _c = cache or _cache
    target_date = for_date or date.today()
    yf_symbol = ETF_TICKERS[ticker]

    # 1. Cache hit
    if use_cache:
        cached = _c.get_price(ticker, target_date)
        if cached is not None:
            logger.debug("Cache hit: %s @ %s = %s", ticker, target_date, cached)
            return cached

    # 2. Live fetch with retry
    def _fetch_live() -> Decimal:
        import yfinance as yf  # lazy import
        hist = yf.Ticker(yf_symbol).history(period="5d")
        if hist.empty:
            raise RuntimeError(f"yfinance returned empty history for {yf_symbol}")
        close = hist["Close"].iloc[-1]
        return Decimal(str(round(close, 4)))

    try:
        price = _retry(_fetch_live)
        # Use the date of the last available row as canonical date
        import yfinance as yf
        hist = yf.Ticker(yf_symbol).history(period="5d")
        actual_date = hist.index[-1].date() if not hist.empty else target_date
        _c.put_price(ticker, actual_date, price)
        logger.info("Fetched live: %s = %s (%s)", ticker, price, actual_date)
        return price

    except Exception as exc:
        logger.warning("Live fetch failed for %s: %s — trying cache fallback", ticker, exc)

    # 3. Cache fallback — any recent price
    fallback = _c.get_latest_price(ticker)
    if fallback:
        fb_date, fb_price = fallback
        logger.warning("Using stale cache for %s: %s @ %s", ticker, fb_price, fb_date)
        return fb_price

    raise RuntimeError(
        f"Cannot get price for {ticker}: live fetch failed and no cache available."
    )


def fetch_basiszins(year: int, *, cache: Optional[MarketCache] = None) -> Decimal:
    """
    Return Basiszins (§247 BGB) for the given year from Bundesbank API.
    Used for Vorabpauschale calculation in January.

    Falls back to cache if API is unavailable.
    Raises RuntimeError if both fail.
    """
    _c = cache or _cache
    rate_key = "bundesbank_basiszins"
    period = str(year)

    cached = _c.get_rate(rate_key, period)
    if cached is not None:
        logger.debug("Cache hit: Basiszins %s = %s%%", year, cached)
        return cached

    url = BUNDESBANK_URL.format(year=year)

    def _fetch() -> Decimal:
        data = _requests_get(url)
        # Bundesbank JSON structure: dataSets[0].series["0:0:0:0:0"].observations
        try:
            series = data["dataSets"][0]["series"]
            obs = next(iter(series.values()))["observations"]
            # Take the last observation value
            last_val = list(obs.values())[-1][0]
            return Decimal(str(last_val))
        except (KeyError, IndexError, StopIteration) as e:
            raise RuntimeError(f"Unexpected Bundesbank response structure: {e}") from e

    try:
        rate = _retry(_fetch)
        _c.put_rate(rate_key, period, rate)
        logger.info("Fetched Basiszins %s = %s%%", year, rate)
        return rate
    except Exception as exc:
        logger.warning("Bundesbank API failed: %s — trying cache fallback", exc)

    fallback = _c.get_rate(rate_key, period)
    if fallback is not None:
        return fallback

    raise RuntimeError(f"Cannot fetch Basiszins for {year}: API failed, no cache.")


def fetch_ecb_rate(*, cache: Optional[MarketCache] = None) -> Decimal:
    """
    Return most recent ECB deposit facility rate as Decimal (percentage).
    Falls back to cache if API unavailable.
    """
    _c = cache or _cache
    rate_key = "ecb_deposit_rate"
    today_str = date.today().isoformat()

    cached = _c.get_rate(rate_key, today_str)
    if cached is not None:
        return cached

    def _fetch() -> Decimal:
        data = _requests_get(ECB_URL)
        try:
            obs = data["dataSets"][0]["series"]["0:0:0:0:0:0:0"]["observations"]
            last_val = list(obs.values())[-1][0]
            return Decimal(str(last_val))
        except (KeyError, IndexError, StopIteration) as e:
            raise RuntimeError(f"Unexpected ECB response structure: {e}") from e

    try:
        rate = _retry(_fetch)
        _c.put_rate(rate_key, today_str, rate)
        logger.info("Fetched ECB rate = %s%%", rate)
        return rate
    except Exception as exc:
        logger.warning("ECB API failed: %s — trying cache fallback", exc)

    # Any recent cached rate is better than nothing
    with _c._connect() as conn:
        row = conn.execute(
            "SELECT value FROM rates WHERE rate_key=? ORDER BY period DESC LIMIT 1",
            (rate_key,),
        ).fetchone()
    if row:
        try:
            return Decimal(row["value"])
        except InvalidOperation:
            pass

    raise RuntimeError("Cannot fetch ECB deposit rate: API failed, no cache.")


def fetch_all_etf_prices(
    *, cache: Optional[MarketCache] = None
) -> dict[str, Decimal]:
    """Fetch current prices for all configured ETFs. Returns {ticker: price}."""
    prices: dict[str, Decimal] = {}
    for ticker in ETF_TICKERS:
        try:
            prices[ticker] = fetch_etf_price(ticker, cache=cache)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", ticker, exc)
    return prices
