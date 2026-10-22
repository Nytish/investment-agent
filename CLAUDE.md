# APEX 2.0 — Claude Code Session Instructions

**Project:** Personal Investment Mentor for Nitish Bidwe  
**Owner:** nitish.bidwe@gmail.com  
**Location:** /home/claude/apex2/ (dev) | GitHub (canonical)

---

## START OF EVERY SESSION

```bash
cd /home/claude/apex2
python -m pytest tests/ -v        # must be green before any new work
python handoff.py --summary       # see current state
```

If resuming from a checkpoint:
```bash
python handoff.py --restore /tmp/apex_checkpoint.json
```

---

## RELAY MODE (context window protocol)

When your context usage reaches ~50%, proactively run:
```bash
python handoff.py --checkpoint
```
This writes `/tmp/apex_checkpoint.json` with full project state. Tell the user the checkpoint path so Session B can resume cleanly. See `HANDOFF.md` for the full protocol.

---

## ARCHITECTURE (6 layers)

```
Layer 6 — web/apex_dashboard.py       (Streamlit)
Layer 5 — agent/model_router.py       (Ollama qwen3.8:27b-mlx → Gemini 2.5 Flash)
Layer 4 — core/market_feed.py         (yfinance + Bundesbank + ECB + RSS)
Layer 3 — notify/scheduler.py         (Gmail MCP, APScheduler, 7 alert types)
Layer 2 — core/                        (policy, cashflow, buckets, tax_engine,
                                        monte_carlo, gap_analysis, etf_catalogue, portfolio)
Layer 1 — data/                        (financial_profile.yaml, journal.db, market_cache.db)
```

---

## SECURITY — NEVER VIOLATE

- `data/financial_profile.yaml` — **NEVER commit** (gitignored, contains personal finance data)
- `.env` — **NEVER commit** (contains API keys)
- No hardcoded API keys — use env vars: `GEMINI_API_KEY`, etc.
- Bundesbank and ECB APIs are public, no key needed

---

## DECIMAL RULE

**All monetary values use `decimal.Decimal`, never `float`.**  
This is non-negotiable. The tax engine and cashflow engine depend on exact arithmetic.

```python
# CORRECT
from decimal import Decimal
price = Decimal("123.45")

# WRONG — introduces float imprecision
price = 123.45
```

---

## KEY FINANCIAL FACTS (do not hallucinate, use these)

| Fact | Value | Status |
|------|-------|--------|
| Net monthly income | €4,315.34 | UNVERIFIED |
| Kindergeld | €259/month | CONFIRMED |
| Monthly expenses | ~€1,800 listed | INCOMPLETE — unlisted expenses exist |
| Monthly surplus | ~€2,515 | UNVERIFIED |
| Emergency savings | €50,000 Scalable Capital @ 2.5% | CONFIRMED |
| Emergency savings rule | **NEVER INVEST — locked as emergency buffer** | |
| Sparer-Pauschbetrag | **€2,000** (married, Steuerklasse III) | CRITICAL: not €1,000 |
| Abgeltungsteuer | 26.375% (incl. Soli) | |
| FIRE target | €600,000 by age 47 | |
| Steuererklärung 2024 | FILED ✅ | |
| Steuererklärung 2025 | FILED ✅ | |
| Freistellungsauftrag | NOT filed with Scalable Capital | |

---

## ETF TICKERS

```python
ETF_TICKERS = {
    "VWCE": "VWCE.DE",    # Vanguard FTSE All-World — global equity (primary)
    "IWDA": "IWDA.AS",    # iShares MSCI World (Amsterdam, more liquid)
    "IS3N": "IS3N.DE",    # iShares MSCI EM — Emerging Markets
    "IEAG": "IEAG.DE",    # iShares EUR Aggregate Bond
    "IWDP": "IWDP.DE",    # iShares Developed Market Property
}
```

---

## BUILD PHASES (status tracked in handoff.py)

| Phase | Module | Status |
|-------|--------|--------|
| 0 | Bug fixes: sparer_pauschbetrag €2K, cashflow, policy | ✅ Done |
| 1 | `core/tax_engine.py` — Vorabpauschale, Abgeltungsteuer | ⬜ Next |
| 2 | `core/gap_analysis.py` — home purchase gap analysis | ⬜ |
| 3 | `core/monte_carlo.py` — 1000 sim, P5/P25/P50/P75, FIRE | ⬜ |
| 4 | `core/market_feed.py` — yfinance + Bundesbank + ECB | ✅ Done |
| 4b | `core/etf_catalogue.py` — 6 ETFs metadata | ⬜ |
| 5 | `notify/scheduler.py` — opportunity scanner + Gmail | ⬜ |
| 6 | `web/apex_dashboard.py` — Streamlit dashboard | ⬜ |
| 7 | `agent/model_router.py` — Ollama/Gemini routing | ⬜ |

---

## TESTING

```bash
python -m pytest tests/ -v          # all tests
python -m pytest tests/test_X.py   # single file
```

- **Never hit real network in tests** — mock yfinance, Bundesbank, ECB
- One test file per module: `tests/test_market_feed.py`, `tests/test_tax_engine.py`, etc.
- Tests use `tmp_path` fixture for SQLite — never write to `data/` in tests

---

## OPEN BUGS (check with `python handoff.py --summary`)

- **BUG-002**: `report.py` line ~155 hardcodes `72000` for down-payment shortfall → read from profile

---

## DO NOT

- Do NOT put JIRA tickets, internal project codenames in any public document
- Do NOT hallucinate financial values — if unsure, ask
- Do NOT use `float` for money
- Do NOT commit `data/financial_profile.yaml`
- Do NOT invest the €50K emergency buffer — it is locked

---

## MODEL (when running agent layer)

```
Primary:   Ollama qwen3.8:27b-mlx    (Mac Mini M4, 24GB unified memory)
Fallback:  Gemini 2.5 Flash          (cloud, GEMINI_API_KEY env var)
Fallback2: Gemini 1.5 Flash          (secondary cloud)
```

Linux machine (RTX 2000 Ada, 8GB VRAM) → use `qwen3:8b` instead (fits in 8GB).
