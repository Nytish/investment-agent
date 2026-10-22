#!/usr/bin/env python3
"""
handoff.py — APEX Relay Mode: dual-session handoff protocol

Lets Claude Code Session A hand off to Session B when context gets full.

Usage:
  python handoff.py --summary          Print compact project state to stdout
  python handoff.py --checkpoint       Write checkpoint to /tmp/apex_checkpoint.json
  python handoff.py --restore FILE     Print resume instructions from checkpoint

Design:
  Session A (context full) → --checkpoint → file → Session B → --restore → resumes
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent
CHECKPOINT_PATH = Path("/tmp/apex_checkpoint.json")

# ---------------------------------------------------------------------------
# State detection
# ---------------------------------------------------------------------------

def _test_status() -> dict:
    """Run pytest and return pass/fail counts."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=60
        )
        lines = result.stdout.splitlines()
        summary = next((l for l in reversed(lines) if "passed" in l or "failed" in l), "unknown")
        import re
        passed_match = re.search(r'(\d+) passed', result.stdout)
        failed_match = re.search(r'(\d+) failed', result.stdout)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        return {"summary": summary, "passed": passed, "failed": failed}
    except Exception as e:
        return {"summary": f"error: {e}", "passed": 0, "failed": 0}


def _files_status() -> dict:
    """Detect key files and their existence."""
    key_files = [
        "core/market_feed.py",
        "cashflow.py",           # root-level existing modules
        "policy.py",
        "buckets.py",
        "core/tax_engine.py",
        "core/monte_carlo.py",
        "core/gap_analysis.py",
        "core/etf_catalogue.py",
        "core/portfolio.py",
        "notify/scheduler.py",
        "web/apex_dashboard.py",
        "agent/model_router.py",
        "data/financial_profile.yaml",
        "data/journal.db",
        "CLAUDE.md",
        "requirements.txt",
        ".gitignore",
    ]
    return {
        f: (ROOT / f).exists()
        for f in key_files
    }


def _bugs_status() -> list[dict]:
    """Known bugs and their fix status."""
    bugs = []

    # Bug 1: sparer_pauschbetrag
    profile_path = ROOT / "data" / "financial_profile.yaml"
    if profile_path.exists():
        content = profile_path.read_text()
        if "sparer_pauschbetrag_eur: 1000" in content:
            bugs.append({
                "id": "BUG-001",
                "description": "sparer_pauschbetrag_eur = 1000 (should be 2000 for married)",
                "file": "data/financial_profile.yaml",
                "status": "OPEN"
            })
        else:
            bugs.append({
                "id": "BUG-001",
                "description": "sparer_pauschbetrag_eur fixed to 2000 (married, Steuerklasse III)",
                "file": "data/financial_profile.yaml",
                "status": "FIXED"
            })

    # Bug 2: hardcoded €72K in report.py
    report_path = ROOT / "report.py"
    if report_path.exists():
        content = report_path.read_text()
        if "72000" in content:
            bugs.append({
                "id": "BUG-002",
                "description": "report.py line 155 hardcodes €72000 down-payment shortfall",
                "file": "report.py",
                "status": "OPEN"
            })

    return bugs


# ---------------------------------------------------------------------------
# Build project state
# ---------------------------------------------------------------------------

def _build_state() -> dict:
    files = _files_status()
    tests = _test_status()
    bugs = _bugs_status()

    # Determine current phase
    completed_phases = []
    if files["cashflow.py"] and files["policy.py"]:
        completed_phases.append("Phase 0: Bug fixes + existing core (cashflow, policy_engine, buckets, tests x64)")
    if files["core/market_feed.py"]:
        completed_phases.append("Phase 4: market_feed.py (yfinance + Bundesbank + ECB + cache)")
    if files["core/tax_engine.py"]:
        completed_phases.append("Phase 1: tax_engine.py")
    if files["core/gap_analysis.py"]:
        completed_phases.append("Phase 2: gap_analysis.py")
    if files["core/monte_carlo.py"]:
        completed_phases.append("Phase 3: monte_carlo.py")
    if files["core/etf_catalogue.py"]:
        completed_phases.append("Phase 4b: etf_catalogue.py")
    if files["notify/scheduler.py"]:
        completed_phases.append("Phase 5: opportunity scanner + Gmail alerts")
    if files["web/apex_dashboard.py"]:
        completed_phases.append("Phase 6: Streamlit dashboard")
    if files["agent/model_router.py"]:
        completed_phases.append("Phase 7: Agent layer (Ollama/Gemini)")

    # Determine next tasks
    next_tasks = []
    if not files["core/tax_engine.py"]:
        next_tasks.append(
            "Phase 1: Port TaxEngine.ts → core/tax_engine.py with Decimal math. "
            "Key: Vorabpauschale = fund_value × Basiszins × 0.7, capped at price gain, "
            "Teilfreistellung 30% for equity, Abgeltungsteuer 26.375%. "
            "Use fetch_basiszins() from market_feed.py."
        )
    if not files["core/gap_analysis.py"]:
        next_tasks.append(
            "Phase 2: Port GapAnalysisEngine.ts → core/gap_analysis.py. "
            "Inputs: monthly_surplus, home_target, horizon_years, LT_target. "
            "Output: GapAnalysisResult(months_to_home, gap_eur, on_track: bool)."
        )
    if not files["core/monte_carlo.py"]:
        next_tasks.append(
            "Phase 3: Port MonteCarloEngine.ts → core/monte_carlo.py. "
            "1000 simulations, Box-Muller, P5/P25/P50/P75 percentiles. "
            "FIRE target: €600K at age 47. All Decimal."
        )
    if not files["notify/scheduler.py"]:
        next_tasks.append(
            "Phase 5: Opportunity scanner + Gmail alerts. "
            "Detect: ETF drop >5%, rebalance drift >5%, Vorabpauschale January, "
            "FSA threshold, rate change >0.25%, Steuererklärung overdue. "
            "Send via Gmail MCP (already connected in Claude session). "
            "Schedule daily 07:00 check with APScheduler."
        )
    if not files["web/apex_dashboard.py"]:
        next_tasks.append(
            "Phase 6: Streamlit dashboard. "
            "Metrics: emergency buffer, monthly surplus, FIRE progress. "
            "Charts: VWCE 1Y price (plotly), portfolio allocation, Monte Carlo fan. "
            "Run: streamlit run web/apex_dashboard.py"
        )

    return {
        "project": "APEX 2.0 — Personal Investment Mentor",
        "owner": "Nitish Bidwe <nitish.bidwe@gmail.com>",
        "location": ROOT.as_posix(),
        "as_of": datetime.now().isoformat(),
        "architecture": {
            "layer_1": "Data: financial_profile.yaml, journal.db, market_cache.db",
            "layer_2": "Engines: policy, cashflow, buckets, tax_engine, monte_carlo, gap_analysis, etf_catalogue, portfolio",
            "layer_3": "Notify+Schedule: Gmail MCP, APScheduler, 7 alert types",
            "layer_4": "Market Intelligence: yfinance + Bundesbank API + ECB API + RSS",
            "layer_5": "Agent: Ollama qwen3.8:27b-mlx (Mac Mini M4, optional) → Gemini 2.5 Flash fallback",
            "layer_6": "Dashboard: Streamlit"
        },
        "key_context": {
            "savings": "€50,000 Scalable Capital Tagesgeld @ 2.5% — EMERGENCY ONLY, never invest",
            "monthly_surplus": "€2,515/month (unverified — unlisted expenses exist)",
            "fire_target": "€600,000 by age 47",
            "tax": {
                "sparer_pauschbetrag": "€2,000 (married, Steuerklasse III)",
                "abgeltungsteuer": "26.375%",
                "steuererklarung_2024": "NOT FILED — urgent action required",
                "freistellungsauftrag": "NOT FILED — file with Scalable Capital immediately"
            },
            "etfs": {
                "VWCE": "VWCE.DE (Xetra) — global equity, long-term",
                "IWDA": "IWDA.AS (Amsterdam) — MSCI World",
                "IS3N": "IS3N.DE — Emerging Markets",
                "IEAG": "IEAG.DE — EUR Aggregate Bonds",
                "IWDP": "IWDP.DE — Property",
            }
        },
        "completed_phases": completed_phases,
        "tests": tests,
        "bugs": bugs,
        "files": {k: ("EXISTS" if v else "MISSING") for k, v in files.items()},
        "next_3_tasks": next_tasks[:3],
        "security_constraints": [
            ".env must never be committed to git",
            "data/financial_profile.yaml is in .gitignore — never commit",
            "No API keys hardcoded — use env vars (GEMINI_API_KEY, BUNDESBANK_API_KEY if needed)",
            "Bundesbank and ECB APIs are public and require no key",
        ]
    }


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_summary() -> None:
    state = _build_state()
    print(json.dumps({
        "as_of": state["as_of"],
        "completed_phases": state["completed_phases"],
        "tests": state["tests"],
        "bugs": [b for b in state["bugs"] if b["status"] == "OPEN"],
        "next_task": state["next_3_tasks"][0] if state["next_3_tasks"] else "All phases complete",
    }, indent=2))


def cmd_checkpoint() -> None:
    state = _build_state()
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))
    print(f"✅ Checkpoint written: {CHECKPOINT_PATH}")
    print(f"   Tests: {state['tests']['summary']}")
    print(f"   Completed: {len(state['completed_phases'])} phases")
    open_bugs = [b for b in state["bugs"] if b["status"] == "OPEN"]
    if open_bugs:
        print(f"   ⚠ Open bugs: {len(open_bugs)}")
    print(f"\n📋 To resume in a new session:")
    print(f"   python {ROOT}/handoff.py --restore {CHECKPOINT_PATH}")


def cmd_restore(checkpoint_file: str) -> None:
    path = Path(checkpoint_file)
    if not path.exists():
        print(f"❌ Checkpoint not found: {path}", file=sys.stderr)
        sys.exit(1)

    state = json.loads(path.read_text())

    print("=" * 70)
    print("APEX 2.0 — RELAY MODE RESUME INSTRUCTIONS")
    print("=" * 70)
    print(f"\nCheckpoint from: {state.get('as_of', 'unknown')}")
    print(f"Project location: {state.get('location')}")
    print(f"\n--- COMPLETED PHASES ---")
    for phase in state.get("completed_phases", []):
        print(f"  ✅ {phase}")

    print(f"\n--- TEST STATUS ---")
    tests = state.get("tests", {})
    print(f"  {tests.get('summary', 'unknown')} ({tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed)")

    open_bugs = [b for b in state.get("bugs", []) if b["status"] == "OPEN"]
    if open_bugs:
        print(f"\n--- OPEN BUGS (fix these first!) ---")
        for bug in open_bugs:
            print(f"  ⚠ [{bug['id']}] {bug['description']}")
            print(f"     File: {bug['file']}")

    print(f"\n--- NEXT 3 TASKS ---")
    for i, task in enumerate(state.get("next_3_tasks", []), 1):
        print(f"\n  {i}. {task}")

    print(f"\n--- KEY CONTEXT ---")
    ctx = state.get("key_context", {})
    print(f"  Savings: {ctx.get('savings')}")
    print(f"  Surplus: {ctx.get('monthly_surplus')}")
    print(f"  FIRE target: {ctx.get('fire_target')}")
    tax = ctx.get("tax", {})
    print(f"  Sparer-Pauschbetrag: {tax.get('sparer_pauschbetrag')}")
    print(f"  Steuererklärung 2024: {tax.get('steuererklarung_2024')}")

    print(f"\n--- TO CONTINUE ---")
    print(f"  cd {state.get('location')}")
    print(f"  python -m pytest tests/ -v   # verify green before continuing")
    print(f"  # Then implement next task above")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="APEX Relay Mode — dual-session handoff protocol"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="Print compact JSON state")
    group.add_argument("--checkpoint", action="store_true", help="Write checkpoint file")
    group.add_argument("--restore", metavar="FILE", help="Read checkpoint and print resume instructions")

    args = parser.parse_args()

    if args.summary:
        cmd_summary()
    elif args.checkpoint:
        cmd_checkpoint()
    elif args.restore:
        cmd_restore(args.restore)


if __name__ == "__main__":
    main()
