"""Tests for notify/opportunity_scanner.py — no network calls, no Gmail."""
import pytest
from datetime import date
from decimal import Decimal

from notify.opportunity_scanner import (
    Opportunity,
    check_etf_drop,
    check_fsa_low,
    check_new_year_rebalance,
    check_portfolio_drift,
    check_steuererklarung_deadline,
    check_tagesgeld_rate_drop,
    check_vorabpauschale_january,
    scan_all,
)


# ── Opportunity dataclass ────────────────────────────────────────────────────

def test_opportunity_invalid_severity_raises():
    with pytest.raises(ValueError, match="severity"):
        Opportunity(name="X", severity="BAD", subject="s", body="b")


def test_opportunity_valid_severities():
    for sev in ("INFO", "WARN", "ACTION"):
        opp = Opportunity(name="X", severity=sev, subject="s", body="b")
        assert opp.severity == sev


# ── check_etf_drop ──────────────────────────────────────────────────────────

def test_etf_drop_exactly_at_threshold_no_trigger():
    # drop == threshold → no trigger (strictly greater)
    result = check_etf_drop("VWCE", Decimal("95"), Decimal("100"), threshold=Decimal("0.05"))
    assert result is None


def test_etf_drop_above_threshold_triggers():
    result = check_etf_drop("VWCE", Decimal("94"), Decimal("100"), threshold=Decimal("0.05"))
    assert result is not None
    assert result.ticker == "VWCE"
    assert result.severity == "ACTION"
    assert "VWCE" in result.subject
    assert "VWCE" in result.body


def test_etf_drop_price_rise_no_trigger():
    result = check_etf_drop("IWDA", Decimal("110"), Decimal("100"))
    assert result is None


def test_etf_drop_zero_prev_price_no_trigger():
    result = check_etf_drop("VWCE", Decimal("94"), Decimal("0"))
    assert result is None


def test_etf_drop_name_contains_ticker_and_pct():
    result = check_etf_drop("IS3N", Decimal("90"), Decimal("100"))
    assert result is not None
    assert "IS3N" in result.name
    assert result.name.startswith("IS3N_DROP_")


# ── check_portfolio_drift ────────────────────────────────────────────────────

def test_portfolio_drift_one_etf_drifted_triggers():
    current = {"VWCE": Decimal("0.60"), "IEAG": Decimal("0.40")}
    target  = {"VWCE": Decimal("0.80"), "IEAG": Decimal("0.20")}
    result = check_portfolio_drift(current, target)
    assert result is not None
    assert result.severity == "WARN"
    assert "VWCE" in result.body


def test_portfolio_drift_within_threshold_no_trigger():
    current = {"VWCE": Decimal("0.78"), "IEAG": Decimal("0.22")}
    target  = {"VWCE": Decimal("0.80"), "IEAG": Decimal("0.20")}
    result = check_portfolio_drift(current, target)
    assert result is None


def test_portfolio_drift_exact_threshold_no_trigger():
    current = {"VWCE": Decimal("0.75")}
    target  = {"VWCE": Decimal("0.80")}
    # drift = 0.05, threshold = 0.05 → strictly greater required → no trigger
    result = check_portfolio_drift(current, target, threshold=Decimal("0.05"))
    assert result is None


# ── check_vorabpauschale_january ─────────────────────────────────────────────

def test_vorabpauschale_january_first_week_triggers():
    result = check_vorabpauschale_january(date(2026, 1, 3))
    assert result is not None
    assert result.severity == "ACTION"
    assert "Freistellungsauftrag" in result.body


def test_vorabpauschale_january_later_in_month_no_trigger():
    result = check_vorabpauschale_january(date(2026, 1, 8))
    assert result is None


def test_vorabpauschale_march_no_trigger():
    result = check_vorabpauschale_january(date(2026, 3, 15))
    assert result is None


# ── check_fsa_low ────────────────────────────────────────────────────────────

def test_fsa_low_below_threshold_triggers():
    result = check_fsa_low(Decimal("199"), threshold=Decimal("200"))
    assert result is not None
    assert "199" in result.subject or "199.00" in result.subject


def test_fsa_low_at_threshold_no_trigger():
    result = check_fsa_low(Decimal("200"), threshold=Decimal("200"))
    assert result is None


def test_fsa_low_well_above_no_trigger():
    result = check_fsa_low(Decimal("1800"))
    assert result is None


# ── check_tagesgeld_rate_drop ────────────────────────────────────────────────

def test_tagesgeld_small_drop_no_trigger():
    # 0.4% drop < 0.5% threshold
    result = check_tagesgeld_rate_drop(Decimal("0.021"), Decimal("0.025"), threshold=Decimal("0.005"))
    assert result is None


def test_tagesgeld_large_drop_triggers():
    # 0.6% drop > 0.5% threshold
    result = check_tagesgeld_rate_drop(Decimal("0.019"), Decimal("0.025"), threshold=Decimal("0.005"))
    assert result is not None
    assert result.severity == "INFO"


def test_tagesgeld_zero_prev_rate_no_trigger():
    result = check_tagesgeld_rate_drop(Decimal("0.019"), Decimal("0"))
    assert result is None


# ── check_steuererklarung_deadline ───────────────────────────────────────────

def test_steuererklarung_march_triggers():
    result = check_steuererklarung_deadline(date(2026, 3, 1))
    assert result is not None
    assert result.severity == "ACTION"
    assert "31 July" in result.body or "July" in result.body


def test_steuererklarung_august_no_trigger():
    result = check_steuererklarung_deadline(date(2026, 8, 1))
    assert result is None


def test_steuererklarung_december_no_trigger():
    result = check_steuererklarung_deadline(date(2026, 12, 15))
    assert result is None


# ── scan_all ─────────────────────────────────────────────────────────────────

def test_scan_all_nothing_triggered_returns_empty():
    market_data = {
        "etf_prices": {"VWCE": Decimal("100")},
        "etf_prev_prices": {"VWCE": Decimal("100")},
        "ecb_rate_current": Decimal("0.025"),
        "ecb_rate_prev": Decimal("0.025"),
    }
    profile = {"fsa_remaining": Decimal("1800")}
    portfolio = {
        "current_weights": {"VWCE": Decimal("0.80")},
        "target_weights": {"VWCE": Decimal("0.80")},
    }
    result = scan_all(market_data, profile, portfolio, today=date(2026, 10, 22))
    assert result == []


def test_scan_all_multiple_triggered():
    market_data = {
        "etf_prices": {"VWCE": Decimal("90")},      # 10% drop → trigger
        "etf_prev_prices": {"VWCE": Decimal("100")},
        "ecb_rate_current": Decimal("0.015"),        # 1% drop → trigger
        "ecb_rate_prev": Decimal("0.025"),
    }
    profile = {"fsa_remaining": Decimal("50")}       # FSA low → trigger
    portfolio = {}
    # March date → Steuererklärung trigger
    result = scan_all(market_data, profile, portfolio, today=date(2026, 3, 1))
    names = [o.name for o in result]
    assert "VWCE_DROP_10PCT" in names
    assert "TAGESGELD_RATE_DROP" in names
    assert "FSA_LOW" in names
    assert "STEUERERKLARUNG_DEADLINE" in names


def test_scan_all_results_are_opportunity_instances():
    market_data = {
        "etf_prices": {"VWCE": Decimal("90")},
        "etf_prev_prices": {"VWCE": Decimal("100")},
    }
    result = scan_all(market_data, {}, {}, today=date(2026, 6, 15))
    for item in result:
        assert isinstance(item, Opportunity)
        assert item.severity in ("INFO", "WARN", "ACTION")
        assert len(item.subject) > 0


def test_scan_all_january_jan2_triggers_two_date_checks():
    # Jan 2: Vorabpauschale (day ≤7) AND new year rebalance (day == 2)
    result = scan_all({}, {}, {}, today=date(2026, 1, 2))
    names = [o.name for o in result]
    assert "VORABPAUSCHALE_JANUARY" in names
    assert "NEW_YEAR_REBALANCE" in names
