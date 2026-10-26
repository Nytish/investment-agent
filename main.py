"""
main.py — INMarket AI Financial Agent
FastAPI backend + Single Page App frontend.

Run:
    python main.py
    → Open http://localhost:8000

Requirements: pip install -r requirements.txt
Environment:  GEMINI_API_KEY in .env
"""

from __future__ import annotations

import json
import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("inmarket")

# ── App ───────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("INMarket agent starting…")
    logger.info(f"Gemini key: {'✅ set' if os.getenv('GEMINI_API_KEY') else '❌ missing — set in .env'}")
    yield
    logger.info("INMarket shutting down.")


app = FastAPI(
    title="INMarket — Personal Investment Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# API — Profile
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/profile")
def get_profile():
    from core.profile import PROFILE
    return {
        "name": PROFILE.name,
        "age": PROFILE.age,
        "net_monthly": PROFILE.net_monthly,
        "kindergeld": PROFILE.kindergeld_monthly,
        "income_total": PROFILE.monthly_income_total,
        "expenses": PROFILE.monthly_expenses,
        "surplus": PROFILE.monthly_surplus,
        "tagesgeld_balance": PROFILE.tagesgeld_balance,
        "tagesgeld_rate": PROFILE.tagesgeld_rate_pct,
        "revolut_balance": PROFILE.revolut_balance,
        "total_savings": PROFILE.total_savings,
        "etf_invested": PROFILE.etf_invested,
        "fire_target": PROFILE.fire_target,
        "months_covered": PROFILE.months_of_expenses_covered(),
        "sparer_pauschbetrag": PROFILE.sparer_pauschbetrag,
        "freistellungsauftrag": PROFILE.freistellungsauftrag_scalable,
        "steuererklarung_2024": PROFILE.steuererklarung_2024,
        "steuererklarung_2025": PROFILE.steuererklarung_2025,
        "interest_annual": PROFILE.freistellung_interest_annual(),
        "tax_saving_fsa": PROFILE.freistellung_tax_saving(),
        "fire_percent": round(PROFILE.etf_invested / PROFILE.fire_target * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════
# API — Market Data
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/quotes")
def get_quotes():
    """All ETF live quotes."""
    from core.market_data import get_all_quotes
    quotes = get_all_quotes()
    result = {}
    for ticker, q in quotes.items():
        if q:
            result[ticker] = {
                "ticker": q.ticker,
                "name": q.name,
                "price": q.price,
                "prev_close": q.prev_close,
                "change_pct": round(q.change_pct, 2),
                "change_eur": round(q.change_eur, 2),
                "day_high": q.day_high,
                "day_low": q.day_low,
                "week52_high": q.week52_high,
                "week52_low": q.week52_low,
                "dip_pct_from_high": round(q.dip_pct_from_high, 2),
                "is_dip": q.is_dip,
                "role": q.role,
            }
        else:
            result[ticker] = None
    return result


@app.get("/api/history/{ticker}")
def get_history(ticker: str, period: str = "1y"):
    """ETF price history for charting."""
    from core.market_data import get_history as _get_history
    history = _get_history(ticker.upper(), period)
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    return {
        "ticker": history.ticker,
        "dates": history.dates,
        "closes": history.closes,
        "period": history.period,
    }


# ═══════════════════════════════════════════════════════════════════════════
# API — Alerts
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/alerts")
def get_alerts():
    """Scan for buy signals and action items."""
    from core.market_data import get_all_quotes
    from core.alerts import scan_for_alerts
    quotes = get_all_quotes()
    alerts = scan_for_alerts(quotes)
    return [
        {
            "ticker": a.ticker,
            "name": a.name,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "action": a.action,
            "dip_pct": a.dip_pct,
            "color": a.color,
            "icon": a.icon,
            "timestamp": a.timestamp.isoformat(),
        }
        for a in alerts
    ]


# ═══════════════════════════════════════════════════════════════════════════
# API — FIRE Projection
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/fire")
def get_fire_projection(monthly: float = 500.0):
    """FIRE Monte Carlo projection for given monthly investment."""
    from core.fire_calc import run_fire_projection
    scenario = run_fire_projection(monthly_investment=monthly)
    return {
        "monthly_investment": monthly,
        "label": scenario.label,
        "ages": scenario.ages,
        "p10": scenario.p10,
        "p25": scenario.p25,
        "p50": scenario.p50,
        "p75": scenario.p75,
        "p90": scenario.p90,
        "fire_probability_by_47": round(scenario.fire_probability_by_47, 1),
        "median_fire_age": scenario.median_fire_age,
        "fire_target": 600_000,
    }


@app.get("/api/fire/scenarios")
def get_fire_scenarios():
    """Three FIRE scenarios: €300, €500, €1000/month."""
    from core.fire_calc import run_all_scenarios
    scenarios = run_all_scenarios()
    return [
        {
            "label": s.label,
            "monthly_investment": s.monthly_investment,
            "ages": s.ages,
            "p50": s.p50,
            "fire_probability_by_47": round(s.fire_probability_by_47, 1),
            "median_fire_age": s.median_fire_age,
        }
        for s in scenarios
    ]


# ═══════════════════════════════════════════════════════════════════════════
# API — Risk Analysis
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/risk")
def get_risk():
    """Risk metrics for all ETFs."""
    from core.market_data import ETF_TICKERS
    from core.risk import analyse_portfolio_risk
    metrics = analyse_portfolio_risk(list(ETF_TICKERS.values()))
    result = {}
    for ticker, m in metrics.items():
        if m:
            result[ticker] = {
                "ticker": m.ticker,
                "annualised_return": m.annualised_return,
                "annualised_volatility": m.annualised_volatility,
                "sharpe_ratio": m.sharpe_ratio,
                "max_drawdown": m.max_drawdown,
                "current_dip_from_high": m.current_dip_from_high,
                "risk_level": m.risk_level,
                "verdict": m.verdict,
            }
    return result


# ═══════════════════════════════════════════════════════════════════════════
# API — AI Chat (Streaming)
# ═══════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []    # [{"role": "user"|"model", "parts": [text]}]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Stream a Gemini response. Returns SSE text/event-stream.

    Each chunk is a JSON line: {"chunk": "text..."} or {"done": true, "error": "..."}.
    """
    from core.market_data import get_all_quotes, build_market_summary
    from core.alerts import scan_for_alerts
    from core.gemini_client import get_gemini_client, stream_chat

    # Enrich message with live market context
    quotes = get_all_quotes()
    market_summary = build_market_summary(quotes)
    alerts = scan_for_alerts(quotes)
    alert_summary = ""
    if alerts:
        buy_signals = [a for a in alerts if a.severity == "BUY_SIGNAL"]
        if buy_signals:
            alert_summary = f"\nActive buy signals: {', '.join(a.ticker for a in buy_signals)}"

    enriched_message = f"{req.message}\n\n[Context: {market_summary}{alert_summary}]"

    # Build messages in Gemini format
    gemini_history = req.history[:]
    messages = [*gemini_history, {"role": "user", "parts": [enriched_message]}]

    async def generate():
        try:
            model = get_gemini_client()
            for chunk in stream_chat(messages, model=model):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'error': f'Error: {e}', 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# API — Daily Briefing
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/briefing")
def get_briefing():
    """AI-generated daily financial briefing."""
    from core.market_data import get_all_quotes, build_market_summary
    from core.alerts import scan_for_alerts
    from core.fire_calc import run_fire_projection, fire_summary_text
    from core.profile import PROFILE
    from core.gemini_client import chat_once

    quotes = get_all_quotes()
    market_summary = build_market_summary(quotes)
    alerts = scan_for_alerts(quotes)
    scenario = run_fire_projection(500)
    fire_text = fire_summary_text(scenario)

    briefing_prompt = f"""
Generate a concise daily financial briefing for Nitish. Format it as:
1. Market pulse (2-3 sentences on ETF movements)
2. Buy signals or opportunities (if any)
3. FIRE progress note (1 sentence)
4. Today's single recommended action

Market data:
{market_summary}

Active alerts: {len(alerts)} total, {sum(1 for a in alerts if a.severity == 'BUY_SIGNAL')} buy signals

FIRE: {fire_text}

Keep it under 150 words. Be direct. No caveats unless critical.
"""

    try:
        briefing = chat_once(briefing_prompt)
        return {"briefing": briefing, "generated_at": __import__("datetime").datetime.now().isoformat()}
    except Exception as e:
        return {"briefing": f"Briefing unavailable: {e}", "generated_at": ""}


# ═══════════════════════════════════════════════════════════════════════════
# Serve Frontend
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    """Serve the SPA."""
    html_path = Path(__file__).parent / "web" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>web/index.html not found</h1>", status_code=500)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
