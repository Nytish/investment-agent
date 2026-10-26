# INMarket — AI Investment Agent

**Owner:** Nitish Bidwe (nitish.bidwe@gmail.com)  
**Stack:** FastAPI + Gemini 2.5 Flash + yfinance + Chart.js  
**Run:** `./start.sh` → `http://localhost:8000`

---

## QUICK START

```bash
cp .env.example .env          # add GEMINI_API_KEY
./start.sh                    # installs deps, starts server
# → open http://localhost:8000
```

Or manually:
```bash
pip install -r requirements.txt
python main.py
```

---

## ARCHITECTURE

```
main.py                      FastAPI app, all API routes, serves web/index.html
core/
  profile.py                 Hardcoded financial profile (no YAML dependency)
  gemini_client.py           Gemini 2.5 Flash client, streaming + single-shot
  market_data.py             Live ETF quotes and history via yfinance
  fire_calc.py               Monte Carlo FIRE projections (1,000 simulations)
  alerts.py                  Buy signal detection, action item alerts
  risk.py                    Volatility, Sharpe ratio, drawdown metrics
web/
  index.html                 Single-page app (dark theme, Chart.js charts)
data/                        Gitignored — no files committed here
```

**API endpoints:**
- `GET /api/profile` — financial profile snapshot
- `GET /api/quotes` — live ETF prices (VWCE, IWDA, IS3N, IEAG, IWDP)
- `GET /api/history/{ticker}?period=1y` — price history for charts
- `GET /api/alerts` — buy signals and action items
- `GET /api/fire?monthly=500` — Monte Carlo FIRE projection
- `GET /api/fire/scenarios` — 3-scenario comparison (€300/€500/€1000)
- `GET /api/risk` — risk metrics for all ETFs
- `POST /api/chat` — SSE streaming chat with Gemini
- `GET /api/briefing` — AI-generated daily briefing
- `GET /` — serves the SPA

---

## ETF UNIVERSE (only these — no others)

```python
ETF_TICKERS = {
    "VWCE": "VWCE.DE",   # Vanguard FTSE All-World — primary holding
    "IWDA": "IWDA.AS",   # iShares MSCI World — developed markets
    "IS3N": "IS3N.DE",   # iShares MSCI EM — emerging markets
    "IEAG": "IEAG.DE",   # iShares EUR Aggregate Bond — bonds
    "IWDP": "IWDP.DE",   # iShares Developed Property — real estate
}
```

---

## KEY FINANCIAL FACTS (hardcoded in core/profile.py — do not hallucinate)

| Fact | Value |
|------|-------|
| Net monthly income | €4,315.34 |
| Kindergeld | €259/month |
| Monthly expenses | ~€1,800 (estimate — unlisted expenses exist) |
| Monthly surplus | ~€2,574 |
| Emergency buffer | **€50,000 Scalable Capital @ 2.5% — NEVER invest** |
| Sparer-Pauschbetrag | **€2,000** (married, Steuerklasse III — NOT €1,000) |
| Abgeltungsteuer | 26.375% (25% + 5.5% Soli) |
| FIRE target | €600,000 |
| ETF invested | €0 (not started) |
| Freistellungsauftrag | NOT filed with Scalable Capital |
| Steuererklärung 2024 | FILED ✅ |
| Steuererklärung 2025 | FILED ✅ |

---

## SECURITY — NEVER VIOLATE

- `.env` — **NEVER commit** (contains GEMINI_API_KEY)
- `data/` — **NEVER commit** (gitignored)
- No hardcoded API keys anywhere — only `os.getenv("GEMINI_API_KEY")`
- Do NOT put internal codenames or personal IDs in any public document

---

## DEVELOPMENT NOTES

- Profile data lives in `core/profile.py` as a frozen dataclass — no YAML file needed
- yfinance quotes are fetched live (no cache) on every `/api/quotes` call
- History is cached 1 hour in-process to avoid hammering yfinance
- Gemini streaming uses SSE — each chunk is `data: {"chunk": "text"}\n\n`
- The SPA is a single `web/index.html` file — no build step, no npm
- Monte Carlo uses a fixed seed (42) for reproducible results

---

## DO NOT

- Do NOT use `float` for production monetary calculations — extend to `Decimal` if needed
- Do NOT add new ETFs outside the approved universe
- Do NOT invest or recommend touching the €50K Tagesgeld emergency buffer
- Do NOT hallucinate financial values — check `core/profile.py` for exact numbers
- Do NOT add YAML/JSON config files — profile stays hardcoded in Python

---

*Last updated: October 2026 | Rebuild from APEX 2.0 (scrapped)*
