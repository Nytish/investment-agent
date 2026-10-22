"""
system_prompt.py — Build the APEX system prompt from live profile + market snapshot.

Nitish's real values are hardcoded as fallbacks so APEX works correctly
even when financial_profile.yaml has not been set up on this machine.
"""

from __future__ import annotations


# ── Nitish's confirmed values (fallback when profile.yaml is absent/incomplete) ─
_DEFAULTS = {
    "net_monthly":            4315.34,
    "kindergeld_monthly":     259.00,
    "monthly_expenses":       1800.00,   # approximate — unlisted expenses exist
    "monthly_surplus":        2515.00,   # net + kindergeld - expenses
    "emergency_savings":      50000.00,  # Scalable Capital Tagesgeld @ 2.5%
    "tagesgeld_rate_pct":     2.50,
    "sparer_pauschbetrag":    2000.00,   # married, Steuerklasse III
    "fire_target":            600000.00,
    "current_age":            36,
    "steuererklarung_2024":   "FILED ✅",
    "steuererklarung_2025":   "FILED ✅",
    "freistellungsauftrag":   "NOT YET FILED with Scalable Capital",
    "etf_invested":           0.00,      # not yet started
}


def _read(profile: dict, *keys, default=None):
    """Safely read a nested key chain from profile dict."""
    node = profile
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
        if node is None:
            return default
    return node


def build_system_prompt(profile: dict, market_snapshot: str = "") -> str:
    """
    Build a context-rich system prompt from live profile values and market data.
    Falls back to hardcoded defaults when profile keys are absent.
    """
    # ── Extract from YAML nested structure, fall back to hardcoded defaults ──
    net_monthly   = _read(profile, "income", "net_monthly",         default=_DEFAULTS["net_monthly"])
    kindergeld    = _read(profile, "income", "kindergeld_monthly",  default=_DEFAULTS["kindergeld_monthly"])
    savings       = _read(profile, "savings", "scalable_capital_tagesgeld", "balance",
                          default=_DEFAULTS["emergency_savings"])
    tagesgeld_rate= _read(profile, "savings", "scalable_capital_tagesgeld", "rate_pct",
                          default=_DEFAULTS["tagesgeld_rate_pct"])
    fsa           = _read(profile, "tax", "sparer_pauschbetrag_eur",    default=_DEFAULTS["sparer_pauschbetrag"])
    steuer_2024   = _read(profile, "tax", "steuererklarung_2024",       default=_DEFAULTS["steuererklarung_2024"])
    steuer_2025   = _read(profile, "tax", "steuererklarung_2025",       default=_DEFAULTS["steuererklarung_2025"])
    freistellung  = _read(profile, "tax", "freistellungsauftrag_scalable",
                          default=_DEFAULTS["freistellungsauftrag"])

    # Calculate surplus from components (more accurate than a stored flat value)
    expenses_listed = (
        (_read(profile, "expenses", "rent",                 default=1200) or 0) +
        (_read(profile, "expenses", "groceries",            default=400)  or 0) +
        (_read(profile, "expenses", "electricity_internet", default=100)  or 0) +
        (_read(profile, "expenses", "miscellaneous",        default=200)  or 0)
    )
    surplus = (net_monthly or 0) + (kindergeld or 0) - expenses_listed

    # ── Freistellungsauftrag warning ──────────────────────────────────────────
    freistellung_flag = (
        "⚠️ Freistellungsauftrag NOT yet filed with Scalable Capital — action needed. "
        f"At 2.5% on €{savings:,.0f} = ~€{savings*tagesgeld_rate/100:,.0f}/year interest; "
        f"up to €{fsa:,.0f} is tax-free once filed."
        if freistellung is None or "NOT" in str(freistellung).upper()
        else f"Freistellungsauftrag: {freistellung}"
    )

    # ── Market snapshot section ───────────────────────────────────────────────
    snapshot_section = (
        f"\n## Current Market Snapshot\n{market_snapshot}\n"
        if market_snapshot
        else ""
    )

    return f"""You are APEX, Nitish's personal investment mentor for Germany.
IMPORTANT: Always respond in English, regardless of what language the user writes in.
IMPORTANT: Never invent numbers. If you are unsure of a figure, say so and use the values in this prompt.
IMPORTANT: Do not perform complex tax calculations yourself — say "the APEX tax engine calculates this" and give the formula only.

## Who Nitish Is
- Age: 36, Indian expat, Ingolstadt, Germany. Sole earner, family of 3 (wife Snehal, one child).
- Net monthly income: €{net_monthly:,.2f} (salary) + €{kindergeld:,.2f} (Kindergeld) = €{net_monthly+kindergeld:,.2f} total
- Monthly expenses: ~€{expenses_listed:,.0f} listed (WARNING: unlisted expenses almost certainly exist — do not treat full surplus as investable without a 3-month bank review)
- Estimated monthly surplus: ~€{surplus:,.0f}/month
- Emergency savings: €{savings:,.2f} @ Scalable Capital Tagesgeld ({tagesgeld_rate}% p.a.) — THIS IS LOCKED. Never suggest investing it.
- ETF investments to date: €0 — just starting
- FIRE target: €600,000 (by age 47 = optimistic; realistic P50 at €500/month = age 66)

## Tax Status
- Steuererklärung 2024: {steuer_2024}
- Steuererklärung 2025: {steuer_2025}
- Sparer-Pauschbetrag: €{fsa:,.0f}/year (married, Steuerklasse III) — this is the JOINT allowance, NOT €1,000
- {freistellung_flag}
{snapshot_section}
## Your Rules
1. Respond in English only.
2. All German tax law: Abgeltungsteuer = 26.375% (incl. Soli), Vorabpauschale via §18 InvStG.
3. Sparer-Pauschbetrag for married couple = €2,000 — NEVER say €1,000.
4. Never recommend: crypto, individual stocks, options, leveraged products.
5. Only recommend these instruments: VWCE.DE, IWDA.AS, IS3N.DE, IEAG.DE, IWDP.DE, Euwax Gold II.
6. Be honest and direct — tell Nitish clearly if a goal is unrealistic.
7. Keep answers concise — Nitish is a busy sole earner with limited time.
8. Do not repeat the same caveats in every message — say something useful each turn.
9. Never suggest using the €{savings:,.0f} emergency buffer for investments. It is locked.
10. Steuererklärung 2024 and 2025 are both FILED — do NOT warn about this.

## Key Action Still Needed
- File Freistellungsauftrag (€{fsa:,.0f}) with Scalable Capital — not yet done. Mention this once per session.

## ETF Reference
| Ticker    | Fund                           | Role              |
|-----------|--------------------------------|-------------------|
| VWCE.DE   | Vanguard FTSE All-World Acc    | Core global (primary) |
| IWDA.AS   | iShares MSCI World Acc         | Developed markets |
| IS3N.DE   | iShares MSCI EM Acc            | Emerging markets  |
| IEAG.DE   | iShares EUR Aggregate Bond     | Bond allocation   |
| IWDP.DE   | iShares Developed Property     | Real estate       |
| Euwax II  | Gold ETC (Stuttgart exchange)  | Inflation hedge   |
"""
