"""
Tests for core/market_feed.py

All network calls are mocked — tests never hit real APIs or yfinance.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.market_feed import (
    ETF_TICKERS,
    MarketCache,
    fetch_basiszins,
    fetch_ecb_rate,
    fetch_etf_price,
    fetch_all_etf_prices,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_cache(tmp_path: Path) -> MarketCache:
    """Fresh in-memory SQLite cache for each test."""
    db = tmp_path / "test_market_cache.db"
    return MarketCache(db_path=db)


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


# ---------------------------------------------------------------------------
# MarketCache unit tests
# ---------------------------------------------------------------------------

class TestMarketCache:
    def test_miss_returns_none(self, tmp_cache: MarketCache) -> None:
        assert tmp_cache.get_price("VWCE", TODAY) is None

    def test_put_and_get_price(self, tmp_cache: MarketCache) -> None:
        price = Decimal("123.4567")
        tmp_cache.put_price("VWCE", TODAY, price)
        result = tmp_cache.get_price("VWCE", TODAY)
        assert result == price

    def test_decimal_precision_preserved(self, tmp_cache: MarketCache) -> None:
        # Verify storage doesn't introduce float imprecision
        price = Decimal("99.9999")
        tmp_cache.put_price("IWDA", TODAY, price)
        result = tmp_cache.get_price("IWDA", TODAY)
        assert result == Decimal("99.9999")
        assert isinstance(result, Decimal)

    def test_get_latest_price_returns_most_recent(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_price("VWCE", YESTERDAY, Decimal("100.00"))
        tmp_cache.put_price("VWCE", TODAY, Decimal("101.50"))
        result = tmp_cache.get_latest_price("VWCE")
        assert result is not None
        d, p = result
        assert d == TODAY
        assert p == Decimal("101.50")

    def test_get_latest_price_none_when_empty(self, tmp_cache: MarketCache) -> None:
        assert tmp_cache.get_latest_price("IS3N") is None

    def test_put_and_get_rate(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_rate("bundesbank_basiszins", "2024", Decimal("3.12"))
        result = tmp_cache.get_rate("bundesbank_basiszins", "2024")
        assert result == Decimal("3.12")

    def test_rate_miss_returns_none(self, tmp_cache: MarketCache) -> None:
        assert tmp_cache.get_rate("bundesbank_basiszins", "2099") is None

    def test_purge_old_removes_stale(self, tmp_cache: MarketCache) -> None:
        old_date = TODAY - timedelta(days=91)
        tmp_cache.put_price("VWCE", old_date, Decimal("80.00"))
        tmp_cache.put_price("VWCE", TODAY, Decimal("100.00"))
        removed = tmp_cache.purge_old()
        assert removed == 1
        assert tmp_cache.get_price("VWCE", TODAY) == Decimal("100.00")
        assert tmp_cache.get_price("VWCE", old_date) is None

    def test_put_overwrites_existing(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_price("VWCE", TODAY, Decimal("100.00"))
        tmp_cache.put_price("VWCE", TODAY, Decimal("105.00"))
        assert tmp_cache.get_price("VWCE", TODAY) == Decimal("105.00")


# ---------------------------------------------------------------------------
# fetch_etf_price tests
# ---------------------------------------------------------------------------

def _make_yf_history(price: float):
    """Build a minimal pandas-like mock for yfinance .history()."""
    import pandas as pd
    idx = pd.DatetimeIndex([pd.Timestamp(TODAY)])
    return pd.DataFrame({"Close": [price]}, index=idx)


class TestFetchEtfPrice:
    def test_returns_decimal(self, tmp_cache: MarketCache) -> None:
        mock_hist = _make_yf_history(123.45)
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = mock_hist
            price = fetch_etf_price("VWCE", cache=tmp_cache)
        assert isinstance(price, Decimal)
        assert price == Decimal("123.45")

    def test_cache_hit_skips_yfinance(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_price("VWCE", TODAY, Decimal("200.00"))
        with patch("yfinance.Ticker") as mock_yf:
            price = fetch_etf_price("VWCE", cache=tmp_cache)
            mock_yf.assert_not_called()
        assert price == Decimal("200.00")

    def test_unknown_ticker_raises(self, tmp_cache: MarketCache) -> None:
        with pytest.raises(ValueError, match="Unknown ticker"):
            fetch_etf_price("BOGUS", cache=tmp_cache)

    def test_yfinance_failure_falls_back_to_cache(self, tmp_cache: MarketCache) -> None:
        # Pre-populate stale cache entry
        tmp_cache.put_price("VWCE", YESTERDAY, Decimal("99.00"))

        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.side_effect = RuntimeError("Yahoo down")
            # Must not raise — should return cached value
            price = fetch_etf_price("VWCE", cache=tmp_cache, use_cache=False)
        assert price == Decimal("99.00")

    def test_yfinance_failure_with_no_cache_raises(self, tmp_cache: MarketCache) -> None:
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.side_effect = RuntimeError("Yahoo down")
            with pytest.raises(RuntimeError, match="Cannot get price"):
                fetch_etf_price("VWCE", cache=tmp_cache, use_cache=False)

    def test_empty_history_raises_then_falls_back(self, tmp_cache: MarketCache) -> None:
        import pandas as pd
        tmp_cache.put_price("IWDA", YESTERDAY, Decimal("75.50"))
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = pd.DataFrame()
            price = fetch_etf_price("IWDA", cache=tmp_cache, use_cache=False)
        assert price == Decimal("75.50")

    def test_decimal_precision_no_float_drift(self, tmp_cache: MarketCache) -> None:
        # 0.1 + 0.2 = 0.30000000000000004 in float — must not appear in output
        mock_hist = _make_yf_history(0.1 + 0.2)
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = mock_hist
            price = fetch_etf_price("VWCE", cache=tmp_cache, use_cache=False)
        assert "00000000000000004" not in str(price)


# ---------------------------------------------------------------------------
# fetch_basiszins tests
# ---------------------------------------------------------------------------

BUNDESBANK_RESPONSE = {
    "dataSets": [{
        "series": {
            "0:0:0:0:0": {
                "observations": {
                    "0": [3.12, 0],
                    "1": [3.24, 0],
                }
            }
        }
    }]
}


class TestFetchBasiszins:
    def test_parses_bundesbank_response(self, tmp_cache: MarketCache) -> None:
        with patch("core.market_feed._requests_get", return_value=BUNDESBANK_RESPONSE):
            rate = fetch_basiszins(2024, cache=tmp_cache)
        assert rate == Decimal("3.24")  # last observation
        assert isinstance(rate, Decimal)

    def test_caches_result(self, tmp_cache: MarketCache) -> None:
        with patch("core.market_feed._requests_get", return_value=BUNDESBANK_RESPONSE) as mock_get:
            fetch_basiszins(2024, cache=tmp_cache)
            fetch_basiszins(2024, cache=tmp_cache)  # second call
            assert mock_get.call_count == 1  # only one HTTP call

    def test_api_failure_falls_back_to_cache(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_rate("bundesbank_basiszins", "2024", Decimal("3.00"))
        with patch("core.market_feed._requests_get", side_effect=RuntimeError("API down")):
            rate = fetch_basiszins(2024, cache=tmp_cache)
        assert rate == Decimal("3.00")

    def test_api_failure_no_cache_raises(self, tmp_cache: MarketCache) -> None:
        with patch("core.market_feed._requests_get", side_effect=RuntimeError("API down")):
            with pytest.raises(RuntimeError, match="Cannot fetch Basiszins"):
                fetch_basiszins(2099, cache=tmp_cache)

    def test_malformed_response_raises(self, tmp_cache: MarketCache) -> None:
        with patch("core.market_feed._requests_get", return_value={"bad": "data"}):
            with pytest.raises(RuntimeError):
                fetch_basiszins(2024, cache=tmp_cache)


# ---------------------------------------------------------------------------
# fetch_ecb_rate tests
# ---------------------------------------------------------------------------

ECB_RESPONSE = {
    "dataSets": [{
        "series": {
            "0:0:0:0:0:0:0": {
                "observations": {
                    "0": [4.00, 0],
                    "1": [3.75, 0],
                }
            }
        }
    }]
}


class TestFetchEcbRate:
    def test_parses_ecb_response(self, tmp_cache: MarketCache) -> None:
        with patch("core.market_feed._requests_get", return_value=ECB_RESPONSE):
            rate = fetch_ecb_rate(cache=tmp_cache)
        assert rate == Decimal("3.75")
        assert isinstance(rate, Decimal)

    def test_api_failure_falls_back_to_any_cached_rate(self, tmp_cache: MarketCache) -> None:
        tmp_cache.put_rate("ecb_deposit_rate", "2024-01-01", Decimal("4.00"))
        with patch("core.market_feed._requests_get", side_effect=RuntimeError("ECB down")):
            rate = fetch_ecb_rate(cache=tmp_cache)
        assert rate == Decimal("4.00")


# ---------------------------------------------------------------------------
# fetch_all_etf_prices tests
# ---------------------------------------------------------------------------

class TestFetchAllEtfPrices:
    def test_returns_all_tickers(self, tmp_cache: MarketCache) -> None:
        mock_hist = _make_yf_history(100.0)
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.history.return_value = mock_hist
            prices = fetch_all_etf_prices(cache=tmp_cache)
        assert set(prices.keys()) == set(ETF_TICKERS.keys())
        assert all(isinstance(p, Decimal) for p in prices.values())

    def test_partial_failure_returns_available(self, tmp_cache: MarketCache) -> None:
        """If one ETF fails, others still return."""
        call_count = [0]

        def side_effect(symbol):
            ticker_mock = MagicMock()
            call_count[0] += 1
            if symbol == "VWCE.DE":
                ticker_mock.history.side_effect = RuntimeError("VWCE down")
            else:
                ticker_mock.history.return_value = _make_yf_history(100.0)
            return ticker_mock

        with patch("yfinance.Ticker", side_effect=side_effect):
            prices = fetch_all_etf_prices(cache=tmp_cache)

        # VWCE should be missing (no cache either), others present
        assert "VWCE" not in prices
        assert len(prices) == len(ETF_TICKERS) - 1
