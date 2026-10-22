"""
report.py — APEX 2.0
Generates a plain-text financial status report from local data only.
No network. No LLM. No cloud.
"""
from __future__ import annotations
import datetime
from decimal import Decimal
from pathlib import Path

from cashflow import (
    load_profile, calculate_income, calculate_expenses,
    calculate_surplus, calculate_savings, months_of_expenses_covered,
    estimate_annual_interest,
)
from buckets import allocate_buckets, BucketStatus
from journal import (
    initialise, get_open_questions, get_recent_decisions,
    log_open_question, log_decision,
)

# Core engines — import with fallback so report.py still runs if core/ not on path
try:
    import sys as _sys
    _sys.path.insert(0, str(__file__[: __file__.rfind("/")]) + "/core")
    from tax_engine import (
        KNOWN_BASISZINS,
        annual_fsa_summary,
        calculate_vorabpauschale,
    )
    _TAX_ENGINE_AVAILABLE = True
except ImportError:
    _TAX_ENGINE_AVAILABLE = False

try:
    import sys as _sys2
    _sys2.path.insert(0, str(__file__[: __file__.rfind("/")]) + "/core")
    from gap_analysis import calculate_home_gap, calculate_fire_gap
    _GAP_ENGINE_AVAILABLE = True
except ImportError:
    _GAP_ENGINE_AVAILABLE = False

try:
    import sys as _sys3
    _sys3.path.insert(0, str(__file__[: __file__.rfind("/")]) + "/core")
    from monte_carlo import SimulationConfig, run_simulation, monthly_needed_for_fire_by_age
    _MONTE_CARLO_AVAILABLE = True
except ImportError:
    _MONTE_CARLO_AVAILABLE = False


SEPARATOR = "=" * 62


def _eur(val: Decimal) -> str:
    return f"€{val:>12,.2f}"


def _pct(val: Decimal) -> str:
    return f"{val:.1f}%"


def _generate_tax_section(
    lines: list,
    profile: dict,
    savings,
    annual_interest: Decimal,
) -> None:
    """Render the German tax summary section into `lines`."""
    a = lines.append
    tax = profile.get("tax", {})
    sparer = Decimal(str(tax.get("sparer_pauschbetrag_eur", 2000)))
    current_year = datetime.datetime.now().year
    prev_year = current_year - 1

    a("\n🧾  GERMAN TAX SUMMARY")
    a(f"  Sparer-Pauschbetrag    €{sparer:,.2f}/year  (married, Steuerklasse III)")
    a(f"  Steuererklärung {prev_year}   {tax.get('steuererklarung_2024', 'STATUS UNKNOWN')}")
    fsa_status = tax.get("freistellungsauftrag_scalable") or "NOT FILED — file before year-end"
    a(f"  Freistellungsauftrag   {fsa_status}")

    if _TAX_ENGINE_AVAILABLE:
        # Tagesgeld interest: estimated tax exposure
        a(f"\n  📊 INTEREST INCOME ANALYSIS ({current_year})")
        a(f"     Est. gross interest     €{annual_interest:>9,.2f}  (Scalable Capital @ 2.50%)")
        a(f"     Sparer-Pauschbetrag   - €{sparer:>9,.2f}")
        if annual_interest > sparer:
            taxable_interest = annual_interest - sparer
            tax_on_interest = (taxable_interest * Decimal("0.26375")).quantize(Decimal("0.01"))
            a(f"     ─────────────────────────────────────────────────")
            a(f"     Taxable interest        €{taxable_interest:>9,.2f}  🚨 OVER FSA LIMIT")
            a(f"     Est. tax due            €{tax_on_interest:>9,.2f}  (26.375% Abgeltungsteuer)")
            a(f"     → File Freistellungsauftrag with Scalable Capital immediately.")
        else:
            a(f"     ─────────────────────────────────────────────────")
            a(f"     Taxable interest        €        0.00  ✅ within FSA")
            remaining_fsa = sparer - annual_interest
            a(f"     FSA remaining for ETFs  €{remaining_fsa:>9,.2f}")

        # Vorabpauschale: no ETF holdings yet → €0
        basiszins_prev = KNOWN_BASISZINS.get(prev_year, Decimal("0"))
        a(f"\n  📊 VORABPAUSCHALE {prev_year}")
        a(f"     Bundesbank Basiszins    {basiszins_prev * 100:.2f}%")
        a(f"     ETF holdings            €        0.00  (none — not yet invested)")
        a(f"     Vorabpauschale          €        0.00  (no ETF holdings)")
        a(f"     → Once ETF savings plan is active, APEX will calculate")
        a(f"        Vorabpauschale automatically each January.")

        # FSA planning note
        a(f"\n  📊 FREISTELLUNGSAUFTRAG PLANNING")
        a(f"     Total FSA allowance     €{sparer:>9,.2f}  (married, §20(9) EStG)")
        a(f"     Est. interest income    €{annual_interest:>9,.2f}")
        if annual_interest >= sparer:
            a(f"     Remaining for ETFs      €        0.00  ⚠  FSA fully consumed by interest")
        else:
            etf_fsa_available = sparer - annual_interest
            a(f"     Remaining for ETFs      €{etf_fsa_available:>9,.2f}  (available for Vorabpauschale)")

    a(f"\n  ⚠  Tax information is for planning only — not legally binding.")
    a(f"     Consult a Steuerberater for binding advice.")


def generate_report(profile_path: Path, output_path: Path | None = None) -> str:
    profile  = load_profile(profile_path)
    income   = calculate_income(profile)
    expenses = calculate_expenses(profile)
    surplus  = calculate_surplus(income, expenses)
    savings  = calculate_savings(profile)
    annual_interest = estimate_annual_interest(savings)

    coverage = months_of_expenses_covered(savings.total_savings, expenses.total_listed)

    allocation = allocate_buckets(
        total_savings=savings.total_savings,
        monthly_expenses=expenses.total_listed,
        emergency_months=6,          # provisional — user has not confirmed
        home_purchase_target=None,   # not yet confirmed
        monthly_surplus=surplus.gross_surplus,   # illustrative — unverified
        house_savings_already=None,              # none saved toward house yet
    )

    goals = profile.get("goals", {})
    tax   = profile.get("tax", {})
    home  = goals.get("home_purchase", {})
    lt    = goals.get("long_term_wealth", {})

    lines = []
    a = lines.append

    a(SEPARATOR)
    a("  APEX 2.0 — FINANCIAL STATUS REPORT")
    a(f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} (local, Europe/Berlin)")
    a(f"  ⚠  ILLUSTRATIVE — based on planning inputs, not verified statements")
    a(SEPARATOR)

    # ── Income ──────────────────────────────────────────────────────────
    a("\n📥  MONTHLY INCOME")
    a(f"  Net salary          {_eur(income.net_monthly)}   [{income.verification_status}]")
    a(f"  Kindergeld          {_eur(income.kindergeld)}   [CONFIRMED — €259/month]")
    a(f"  ─────────────────────────────────────────────────────")
    a(f"  Total               {_eur(income.total_monthly)}")

    # ── Expenses ─────────────────────────────────────────────────────────
    a("\n📤  MONTHLY EXPENSES  (listed only — likely incomplete)")
    a(f"  Rent                {_eur(expenses.rent)}")
    a(f"  Groceries           {_eur(expenses.groceries)}")
    a(f"  Electricity/Net     {_eur(expenses.electricity_internet)}")
    a(f"  Miscellaneous       {_eur(expenses.miscellaneous)}")
    a(f"  ─────────────────────────────────────────────────────")
    a(f"  Total listed        {_eur(expenses.total_listed)}   [{expenses.verification_status}]")
    a(f"  ⚠  Unlisted items likely include: insurance (Haftpflicht, Hausrat),")
    a(f"     phone, transport, clothing, childcare, subscriptions.")
    a(f"     → Review 3 months of bank statements to find actual total.")

    # ── Surplus ──────────────────────────────────────────────────────────
    a("\n💡  SURPLUS  (before unlisted expenses)")
    a(f"  Gross surplus       {_eur(surplus.gross_surplus)}   [UNVERIFIED]")
    a(f"  ⚠  True investable surplus is likely €500–€1,500 lower than shown.")
    a(f"     Do not commit a monthly investment amount until expenses are verified.")

    # ── Savings ──────────────────────────────────────────────────────────
    a("\n🏦  SAVINGS")
    if savings.revolut_balance > Decimal("0"):
        a(f"  Revolut ({_pct(savings.revolut_rate)} p.a.)  {_eur(savings.revolut_balance)}")
    a(f"  Scalable Tagesgeld  {_eur(savings.scalable_balance)}   [{savings.verification_status}]")
    a(f"    Rate: {_pct(savings.scalable_rate)} p.a.  |  Confirmed by user 2026-10-21")
    a(f"  ─────────────────────────────────────────────────────")
    a(f"  Total savings       {_eur(savings.total_savings)}")
    a(f"  Expense coverage    {coverage} months  (of listed expenses only)")
    a(f"  Est. gross interest {_eur(annual_interest)} / year  (at current rates)")

    # Interest tax note
    sparer = Decimal(str(tax.get("sparer_pauschbetrag_eur", 2000)))
    if annual_interest > sparer:
        taxable = annual_interest - sparer
        tax_est = (taxable * Decimal("0.26375")).quantize(Decimal("0.01"))  # 25% KESt + 5.5% Soli
        a(f"\n  🚨 TAX ALERT: Estimated interest (€{annual_interest:.2f}) exceeds")
        a(f"     Sparer-Pauschbetrag (€{sparer:.2f}) by €{taxable:.2f}.")
        a(f"     Estimated tax due: ~€{tax_est:.2f}  (25% KESt + Soli, no church tax).")
        a(f"     → File a Freistellungsauftrag with Scalable Capital immediately.")
        a(f"     → Consider splitting savings across a second account to use allowance fully.")

    # ── Bucket allocation ────────────────────────────────────────────────
    a("\n🪣  ZONE 1 — EXISTING SAVINGS  (€50,000 Scalable Capital — LOCKED)")
    a(f"  This money does NOT move. It is your emergency buffer, nothing else.")
    a(f"  {'Bucket':<28} {'Balance':>12}  {'Target':>13}  Status")
    a(f"  {'─'*28} {'─'*12}  {'─'*13}  {'─'*13}")
    b = allocation.emergency
    tgt = f"€{b.target:>11,.2f}" if b.target else "   UNCONFIRMED"
    icon = "✅" if b.status == BucketStatus.FUNDED else "⚠ "
    a(f"  {icon} {b.name:<26} {_eur(b.balance)}  {tgt}  {b.status.value}")
    a(f"")
    a(f"  Emergency target: 6 months × €{expenses.total_listed:,.2f} = €{6*expenses.total_listed:,.2f}")
    a(f"  Your €50,000 covers {coverage} months of listed expenses — very well buffered.")
    a(f"  Note: use VERIFIED monthly expenses (will be higher) for a true target.")

    a("\n🪣  ZONE 2 — FUTURE MONTHLY SURPLUS  (building from here)")
    a(f"  House fund and long-term investing are built from NEW savings each month.")
    a(f"  The €50K emergency buffer is never touched for these goals.")
    a(f"  {'Bucket':<28} {'Saved':>12}  {'Target':>13}  Status")
    a(f"  {'─'*28} {'─'*12}  {'─'*13}  {'─'*13}")
    for b in [allocation.home_purchase, allocation.long_term]:
        tgt = f"€{b.target:>11,.2f}" if b.target else "   UNCONFIRMED"
        icon = "✅" if b.status == BucketStatus.FUNDED else "⚠ "
        a(f"  {icon} {b.name:<26} {_eur(b.balance)}  {tgt}  {b.status.value}")

    # ── Property context ─────────────────────────────────────────────────
    a("\n🏠  PROPERTY GOAL  (planning context — unconfirmed)")
    a(f"  Target area         {home.get('target_location', 'UNCONFIRMED')}")
    a(f"  Horizon             ~{home.get('horizon_years', 3)} years")
    a(f"  Target price        UNCONFIRMED  ← must be set")
    a(f"  Down-payment %      UNCONFIRMED  ← must be set")
    a("")
    ref = home.get("reference_prices", {})
    if ref:
        a(f"  📊 APPROXIMATE MARKET REFERENCE  (2025 estimates — research current listings)")
        a(f"     Ingolstadt  80m²  ~€{ref.get('typical_80sqm_ingolstadt', 0):>9,}   (~€{ref.get('ingolstadt_apt_per_sqm', 0):,}/m²)")
        a(f"     Munich      80m²  ~€{ref.get('typical_80sqm_munich', 0):>9,}   (~€{ref.get('munich_apt_per_sqm', 0):,}/m²)")
        a(f"")
        a(f"  💡 YOUR SAVINGS vs. PROPERTY SCENARIOS")
        a(f"     If Ingolstadt ~€360K  →  20% down = €72K  |  30% down = €108K")
        a(f"     If Munich     ~€720K  →  20% down = €144K |  30% down = €216K")
        a(f"     Current savings: €{savings.total_savings:,.2f}")

        if _GAP_ENGINE_AVAILABLE:
            # Dynamic gap analysis — no hardcoded figures (BUG-002 fixed)
            ingolstadt_price = Decimal(str(ref.get("typical_80sqm_ingolstadt", 360000)))
            _home_gap = calculate_home_gap(
                target_price=ingolstadt_price,
                down_pct=Decimal("0.20"),
                current_savings=savings.total_savings,
                monthly_surplus=surplus.gross_surplus,
            )
            if _home_gap.already_covered:
                a(f"     ✅ Down payment for Ingolstadt at 20% is already covered by savings.")
            else:
                a(f"     ⚠  For Ingolstadt at 20% down, shortfall is €{_home_gap.shortfall:,.2f}.")
                if _home_gap.months_to_target > 0:
                    a(f"        At current surplus (€{surplus.gross_surplus:,.2f}/month): "
                      f"{_home_gap.months_to_target} months ({_home_gap.years_to_target} years) to close gap.")
                else:
                    a(f"        Cannot close gap — monthly surplus is zero or negative.")
            a(f"        Munich is financially out of reach on current savings without significant growth.")
        else:
            a(f"     ⚠  Gap engine not available — install core/gap_analysis.py for dynamic analysis.")

        a(f"     → The 3-year timeline is achievable for Ingolstadt IF:")
        a(f"       (a) property prices don't rise sharply, and")
        a(f"       (b) you save ~€1,200–€1,500/month consistently, and")
        a(f"       (c) down-payment is placed in capital-stable accounts (not equities).")

    # ── Risk & investments ───────────────────────────────────────────────
    a("\n📊  INVESTMENT PROFILE")
    a(f"  Risk tolerance      {lt.get('risk_tolerance', 'UNCONFIRMED').upper()}  [{lt.get('risk_tolerance_status', '')}]")
    a(f"  Permitted assets    UNCONFIRMED  ← must be confirmed before any recommendation")
    a(f"")
    a(f"  💡 Given low-to-moderate risk tolerance, typical allocation for discussion:")
    a(f"     • Home-purchase fund (3-yr horizon) → Tagesgeld / money-market only")
    a(f"     • Emergency reserve                 → Tagesgeld / instant access only")
    a(f"     • Long-term bucket (if any)         → MSCI World acc. ETF (broad, passive)")
    a(f"     This is illustrative — no recommendation is made until goals are confirmed.")

    # ── FIRE Analysis ────────────────────────────────────────────────────
    if _GAP_ENGINE_AVAILABLE:
        a("\n🔥  FIRE ANALYSIS  (Financial Independence, Retire Early)")
        _annual_expenses = expenses.total_listed * Decimal("12")
        _fire = calculate_fire_gap(
            annual_expenses=_annual_expenses,
            current_invested=Decimal("0"),      # no ETF holdings yet
            monthly_investment=Decimal("0"),    # no ETF savings plan yet
            current_age=36,
            target_fire_age=47,
            assumed_annual_return=Decimal("0.07"),
        )
        a(f"  FIRE target (25× annual expenses)   {_eur(_fire.fire_target)}")
        a(f"  Annual expenses (listed)             {_eur(_annual_expenses)}  ⚠  unverified")
        a(f"  Currently invested                   {_eur(_fire.current_invested)}")
        a(f"  Monthly investment                   {_eur(_fire.monthly_investment)}  (not yet started)")
        a(f"  Assumed real return                  {float(_fire.assumed_annual_return)*100:.1f}% p.a.")
        a(f"")
        # Project with illustrative €500/month
        _illustrative_fire = calculate_fire_gap(
            annual_expenses=_annual_expenses,
            current_invested=Decimal("0"),
            monthly_investment=Decimal("500"),
            current_age=36,
            target_fire_age=47,
            assumed_annual_return=Decimal("0.07"),
        )
        if _illustrative_fire.fire_age < 999:
            a(f"  💡 At €500/month into VWCE @ 7% real return:")
            a(f"     → FIRE reached at age {_illustrative_fire.fire_age} "
              f"({_illustrative_fire.years_to_fire} years from now)")
        a(f"")
        mneed = _fire.monthly_needed_to_hit_age
        if mneed == 0:
            a(f"  To retire at 47: already on track (no new investment needed).")
        elif mneed < 999_999:
            a(f"  To retire at 47: need €{mneed:,}/month invested from now.")
        else:
            a(f"  To retire at 47: mathematically not possible — target horizon too short.")
        a(f"")
        a(f"  ⚠  FIRE analysis uses listed expenses only. True figure is higher.")
        a(f"     Start ETF savings plan to see real projections.")

    # ── Monte Carlo ──────────────────────────────────────────────────────
    if _MONTE_CARLO_AVAILABLE:
        a("\n🎲  MONTE CARLO PROJECTION  (1,000 simulations, 7% mean return, 15% std dev)")
        a(f"  Horizon: 11 years (age 36 → 47)  |  FIRE target: €600,000")
        a("")

        # Illustrative at €500/month (not yet started)
        _mc_cfg = SimulationConfig(
            monthly_investment=Decimal("500"),
            initial_invested=Decimal("0"),
            annual_return_mean=0.07,
            annual_return_std=0.15,
            years=11,
            simulations=1000,
            fire_target=Decimal("600000"),
        )
        _mc = run_simulation(_mc_cfg, seed=42)

        a(f"  Illustrative: €500/month into VWCE  (not yet started)")
        a(f"  At age 47:")
        a(f"    P5  (bad case):       {_eur(_mc.p5[-1])}    (1-in-20 bad outcome)")
        a(f"    P25 (below median):   {_eur(_mc.p25[-1])}")
        a(f"    P50 (median):         {_eur(_mc.p50[-1])}")
        a(f"    P75 (above median):   {_eur(_mc.p75[-1])}")
        a(f"    P95 (great case):     {_eur(_mc.p95[-1])}    (1-in-20 great outcome)")
        a(f"")
        fire_pct = float(_mc.fire_probability) * 100
        a(f"  FIRE probability by age 47:  {fire_pct:.1f}%  (at €500/month)")
        if _mc.median_fire_age:
            a(f"  Median FIRE age:  {_mc.median_fire_age}")
        else:
            a(f"  Median FIRE age:  not reached by age 47 at this rate")
        a(f"")
        # Monthly needed for 50% FIRE probability by age 47
        _monthly_needed = monthly_needed_for_fire_by_age(
            fire_target=Decimal("600000"),
            initial_invested=Decimal("0"),
            target_age=47,
            current_age=36,
            annual_return_mean=0.07,
            seed=42,
        )
        if _monthly_needed > Decimal("0"):
            a(f"  → For 50% FIRE probability by age 47: invest €{_monthly_needed:,.0f}/month")
        else:
            a(f"  → FIRE by age 47 is not achievable with current parameters")
        a(f"")
        a(f"  ⚠  Simulations use historical equity return assumptions (7% real, 15% vol).")
        a(f"     Past performance does not guarantee future results.")
        a(f"     Start investing first — every month of delay reduces all percentiles.")

    # ── Tax ──────────────────────────────────────────────────────────────
    _generate_tax_section(lines, profile, savings, annual_interest)

    # ── Open questions ───────────────────────────────────────────────────
    open_qs = get_open_questions()
    a(f"\n❓  OPEN QUESTIONS  ({len(open_qs)} remaining)")
    if open_qs:
        for q in open_qs:
            a(f"  [{q['id']}] {q['question']}")
    else:
        a("  None — all inputs confirmed. ✅")

    # ── Journal ──────────────────────────────────────────────────────────
    recent = get_recent_decisions(limit=5)
    a(f"\n📒  RECENT JOURNAL  ({len(recent)} entries shown)")
    if recent:
        for d in recent:
            asset = d['asset'] or '—'
            a(f"  [{d['ts']}] {d['action']:12}  {asset:15}  {str(d['rationale'])[:55]}")
    else:
        a("  No decisions logged yet.")

    # ── Next actions ─────────────────────────────────────────────────────
    a(f"\n🎯  REQUIRED ACTIONS  (priority order)")
    a(f"  🚨 1. FILE Steuererklärung 2024  — tax obligation, overdue")
    a(f"  🚨 2. FILE Freistellungsauftrag with Scalable Capital  — you are over the €1,000 limit")
    a(f"     3. CONFIRM emergency reserve months (default: 6, = €11,400)")
    a(f"     4. RESEARCH and SPECIFY property target price + location")
    a(f"     5. VERIFY actual monthly expenses from 3 months of bank statements")
    a(f"     6. CONFIRM permitted investment instruments")
    a(f"     7. Set up Trade Republic ETF savings plan  (after items 4–6 confirmed)")
    a(f"")
    a(f"  Current system status: NO INVESTMENT RECOMMENDATION")
    a(f"  Reason: property goal unconfirmed → all savings protected.")
    a(f"  This is correct — the system is working as designed.")

    a("\n" + SEPARATOR)
    a("  END OF REPORT")
    a("  Privacy: all data local | no network used | no cloud inference")
    a(SEPARATOR)

    report_text = "\n".join(lines)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")

    return report_text


if __name__ == "__main__":
    from pathlib import Path

    initialise()
    existing_texts = {q["question"] for q in get_open_questions()}

    open_questions = [
        "What is your minimum acceptable emergency reserve (months of expenses)?",
        "What is your target property purchase price (EUR)?",
        "Which city/town near Ingolstadt or Munich are you targeting for property?",
        "What down-payment percentage do you plan to use (e.g. 20% or 30%)?",
        "Which investment instruments do you permit? (e.g. MSCI World acc. ETF)",
        "Have you filed a Freistellungsauftrag with Scalable Capital? (urgent — over €1,000 limit)",
    ]
    for q in open_questions:
        if q not in existing_texts:
            log_open_question(q)

    profile_path = Path(__file__).parent / "data" / "financial_profile.yaml"
    output_path  = Path(__file__).parent / "reports" / "status_report.txt"

    report = generate_report(profile_path, output_path)
    print(report)
