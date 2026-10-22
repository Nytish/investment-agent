"""
tests/test_tax_engine.py — APEX 2.0
Unit tests for core/tax_engine.py.

All test values use real German tax numbers and verified arithmetic.
No network calls. No float arithmetic.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

# Allow importing from repo root and core/
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from tax_engine import (
    ABGELTUNGSTEUER_RATE,
    KNOWN_BASISZINS,
    VorabpauschaleResult,
    RealisationResult,
    annual_fsa_summary,
    calculate_realisation_tax,
    calculate_vorabpauschale,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

D = Decimal  # shorthand


# ── Vorabpauschale tests ─────────────────────────────────────────────────────

class TestVorabpauschale:

    def test_standard_2024_fsa_covers_all(self):
        """
        2024 standard case: Basiszins 2.29%, €10K fund, €1,200 gain.
        FSA of €2,000 fully covers the taxable amount → tax_due = €0.

        Arithmetic:
          base_return  = 10000 × 0.0229 × 0.70 = 160.30
          taxable_base = min(160.30, 1200) × 0.70 = 112.21
          fsa_applied  = 112.21  (€2,000 FSA covers it)
          tax_due      = €0.00
        """
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("11200"),
            basiszins=D("0.0229"),
            fsa_remaining=D("2000"),
            is_equity_fund=True,
        )
        assert result.year == 2024
        assert result.basiszins == D("0.0229")
        assert result.fund_value == D("10000")
        assert result.price_gain == D("1200")
        assert result.base_return == D("160.30")
        assert result.taxable_base == D("112.21")
        assert result.fsa_applied == D("112.21")
        assert result.fsa_remaining_after == D("1887.79")
        assert result.tax_due == D("0.00")

    def test_no_price_gain_zero_tax(self):
        """Fund did not increase → price_gain = 0 → no Vorabpauschale."""
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("10000"),  # flat
            basiszins=D("0.0229"),
            fsa_remaining=D("2000"),
        )
        assert result.price_gain == D("0")
        assert result.taxable_base == D("0.00")
        assert result.tax_due == D("0.00")
        assert result.fsa_applied == D("0.00")
        assert result.fsa_remaining_after == D("2000")

    def test_fund_fell_zero_tax(self):
        """Fund lost value → price_gain = 0 → no Vorabpauschale."""
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("9500"),   # fell
            basiszins=D("0.0229"),
            fsa_remaining=D("2000"),
        )
        assert result.price_gain == D("0")
        assert result.tax_due == D("0.00")

    def test_fsa_exhausted_full_tax(self):
        """
        When FSA = €0, the full taxable_base is taxed.

        base_return  = 10000 × 0.0229 × 0.70 = 160.30
        taxable_base = min(160.30, 1200) × 0.70 = 112.21
        tax_due      = 112.21 × 0.26375 = 29.60
        """
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("11200"),
            basiszins=D("0.0229"),
            fsa_remaining=D("0"),
        )
        assert result.fsa_applied == D("0.00")
        assert result.fsa_remaining_after == D("0.00")
        # 112.21 × 0.26375 = 29.595... → rounds to 29.60
        assert result.tax_due == D("29.60")

    def test_base_return_capped_at_price_gain(self):
        """
        If base_return > price_gain, Vorabpauschale is capped at price_gain.

        E.g. high Basiszins 10%, €10K fund, only €50 gain:
          base_return  = 10000 × 0.10 × 0.70 = 700.00
          capped at    = 50.00
          taxable_base = 50.00 × 0.70 = 35.00
        """
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("10050"),  # only €50 gain
            basiszins=D("0.10"),        # hypothetical high rate
            fsa_remaining=D("0"),
        )
        assert result.price_gain == D("50")
        assert result.base_return == D("700.00")
        # Capped: min(700.00, 50.00) = 50.00; × 0.70 = 35.00
        assert result.taxable_base == D("35.00")
        # 35.00 × 0.26375 = 9.23125 → 9.23
        assert result.tax_due == D("9.23")

    def test_partial_fsa_usage(self):
        """FSA partially offsets; remainder taxed."""
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("11200"),
            basiszins=D("0.0229"),
            fsa_remaining=D("50"),  # only €50 FSA left
        )
        assert result.fsa_applied == D("50.00")
        after_fsa = D("112.21") - D("50.00")  # = 62.21
        expected_tax = (after_fsa * ABGELTUNGSTEUER_RATE).quantize(Decimal("0.01"))
        assert result.tax_due == expected_tax
        assert result.fsa_remaining_after == D("0.00")

    def test_non_equity_fund_no_teilfreistellung(self):
        """
        Bond ETF (is_equity_fund=False): Teilfreistellung = 100% taxable (no exemption).

        base_return  = 10000 × 0.0229 × 0.70 = 160.30
        taxable_base = min(160.30, 1200) × 1.00 = 160.30
        """
        result = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"),
            fund_value_end=D("11200"),
            basiszins=D("0.0229"),
            fsa_remaining=D("0"),
            is_equity_fund=False,
        )
        assert result.taxable_base == D("160.30")

    def test_known_basiszins_2024_constant(self):
        """Verify the 2024 Basiszins constant matches the directive (2.29%)."""
        assert KNOWN_BASISZINS[2024] == D("0.0229")

    def test_known_basiszins_2023_constant(self):
        """Verify the 2023 Basiszins constant (2.55%)."""
        assert KNOWN_BASISZINS[2023] == D("0.0255")


# ── Realisation tests ─────────────────────────────────────────────────────────

class TestRealisationTax:

    def test_standard_realisation(self):
        """
        buy=€50, sell=€75, 100 units, FSA €500.

        gain         = (75 - 50) × 100 = 2500
        taxable_gain = 2500 × 0.70     = 1750
        fsa_applied  = 500
        after_fsa    = 1250
        tax_due      = 1250 × 0.26375  = 329.69
        """
        result = calculate_realisation_tax(
            buy_price=D("50"),
            sell_price=D("75"),
            units=D("100"),
            fsa_remaining=D("500"),
            is_equity_fund=True,
        )
        assert result.gain == D("2500")
        assert result.taxable_gain == D("1750.00")
        assert result.fsa_applied == D("500.00")
        assert result.fsa_remaining_after == D("0.00")
        # 1250 × 0.26375 = 329.6875 → 329.69
        assert result.tax_due == D("329.69")

    def test_realisation_fsa_covers_all(self):
        """Small gain fully covered by FSA → tax_due = €0."""
        result = calculate_realisation_tax(
            buy_price=D("100"),
            sell_price=D("110"),
            units=D("10"),
            fsa_remaining=D("2000"),
        )
        # gain = 100, taxable = 70
        assert result.gain == D("100")
        assert result.taxable_gain == D("70.00")
        assert result.fsa_applied == D("70.00")
        assert result.tax_due == D("0.00")
        assert result.fsa_remaining_after == D("1930.00")

    def test_realisation_loss_no_tax(self):
        """Selling at a loss → no tax. FSA not consumed."""
        result = calculate_realisation_tax(
            buy_price=D("100"),
            sell_price=D("80"),
            units=D("10"),
            fsa_remaining=D("2000"),
        )
        assert result.gain == D("-200")
        assert result.tax_due == D("0.00")
        assert result.fsa_applied == D("0.00")
        assert result.fsa_remaining_after == D("2000")


# ── Annual FSA summary tests ──────────────────────────────────────────────────

class TestAnnualFsaSummary:

    def test_empty_year_no_holdings(self):
        """No events → no FSA used, no tax."""
        summary = annual_fsa_summary([], [], fsa_total=D("2000"))
        assert summary["fsa_used"] == D("0.00")
        assert summary["fsa_remaining"] == D("2000.00")
        assert summary["total_tax_due"] == D("0.00")
        assert summary["tax_saved"] == D("0.00")

    def test_combined_vorabpauschale_and_realisation(self):
        """
        Year with both Vorabpauschale (€112.21 taxable) and a realisation (€70 taxable).
        Total FSA used = 182.21, FSA remaining = 2000 - 182.21 = 1817.79.
        Both covered by FSA → total_tax_due = €0.
        tax_saved = 182.21 × 0.26375 = 48.06
        """
        vp = calculate_vorabpauschale(
            year=2024,
            fund_value_start=D("10000"), fund_value_end=D("11200"),
            basiszins=D("0.0229"), fsa_remaining=D("2000"),
        )
        remaining_after_vp = vp.fsa_remaining_after

        re = calculate_realisation_tax(
            buy_price=D("100"), sell_price=D("110"), units=D("10"),
            fsa_remaining=remaining_after_vp,
        )

        summary = annual_fsa_summary([vp], [re], fsa_total=D("2000"))
        assert summary["fsa_used"] == D("182.21")
        assert summary["fsa_remaining"] == D("1817.79")
        assert summary["total_tax_due"] == D("0.00")
        # 182.21 × 0.26375 = 48.0579... → 48.06
        assert summary["tax_saved"] == D("48.06")
