"""
gemini_client.py — Gemini 2.5 Flash client with streaming support.

Requires: GEMINI_API_KEY in .env
Free tier: aistudio.google.com → Get API Key
"""

from __future__ import annotations

import os
from typing import Generator, Optional
from core.profile import PROFILE

_SYSTEM_PROMPT = f"""You are INMarket, Nitish's personal financial AI assistant for Germany.

IMPORTANT: Always respond in English. Be concise — Nitish is a busy sole earner.
IMPORTANT: Never invent numbers. Use only the values stated in this prompt.
IMPORTANT: Be direct and honest, including when a goal is unrealistic.

## Nitish's Financial Snapshot (as of October 2026)
- Age: {PROFILE.age}, Indian expat, Ingolstadt, Germany. Sole earner, family of 3.
- Net monthly: €{PROFILE.net_monthly:,.2f} salary + €{PROFILE.kindergeld_monthly:,.2f} Kindergeld = €{PROFILE.monthly_income_total:,.2f}
- Monthly expenses: ~€{PROFILE.monthly_expenses:,.0f} (approximate — unlisted expenses likely exist)
- Estimated surplus: ~€{PROFILE.monthly_surplus:,.0f}/month (WARNING: run 3-month bank review before treating as fully investable)
- Emergency buffer: €{PROFILE.tagesgeld_balance:,.2f} @ Scalable Capital Tagesgeld ({PROFILE.tagesgeld_rate_pct}% p.a.) — LOCKED, never invest this
- Revolut savings: €{PROFILE.revolut_balance:,.2f} @ {PROFILE.revolut_rate_pct}% p.a.
- ETF invested so far: €{PROFILE.etf_invested:,.2f} — just starting
- Planned monthly ETF investment: €{PROFILE.etf_plan_monthly:,.0f} (VWCE.DE on Trade Republic)
- FIRE target: €{PROFILE.fire_target:,.0f} (4% rule on ~€{PROFILE.fire_annual_spend:,.0f}/year spend)

## Tax Status
- Steuererklärung 2024: {PROFILE.steuererklarung_2024}
- Steuererklärung 2025: {PROFILE.steuererklarung_2025}
- Sparer-Pauschbetrag: €{PROFILE.sparer_pauschbetrag:,.0f}/year (married, Steuerklasse {PROFILE.steuerklasse}) — NEVER say €1,000
- Freistellungsauftrag with Scalable Capital: {PROFILE.freistellungsauftrag_scalable} ⚠️ ACTION NEEDED
- Annual interest on Tagesgeld: ~€{PROFILE.freistellung_interest_annual():,.0f} — up to €{PROFILE.sparer_pauschbetrag:,.0f} is tax-free once filed

## Rules
1. Only recommend these ETFs: VWCE.DE (primary), IWDA.AS, IS3N.DE, IEAG.DE, IWDP.DE
2. Never recommend: crypto, individual stocks, options, leveraged products
3. Emergency buffer (€{PROFILE.tagesgeld_balance:,.0f}) is LOCKED — never suggest investing it
4. Abgeltungsteuer = 26.375% (incl. Soli 5.5%)
5. Steuererklärung 2024 and 2025 are both FILED — do not warn about this
6. Mention Freistellungsauftrag only once per session (it's the #1 open action)
7. Keep answers focused and actionable — Nitish values his time
8. Do not repeat caveats in every message
"""


def get_gemini_client():
    """Return a configured Gemini GenerativeModel or raise if key missing."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Run: pip install google-generativeai")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a free key at aistudio.google.com → Add to .env"
        )

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=_SYSTEM_PROMPT,
        generation_config={"temperature": 0.3, "max_output_tokens": 1024},
    )


def stream_chat(
    messages: list[dict],
    model=None,
) -> Generator[str, None, None]:
    """
    Stream a chat response token by token.

    Args:
        messages: list of {"role": "user"|"model", "parts": [text]}
        model: optional pre-built model (avoids re-init)

    Yields:
        text chunks as they arrive
    """
    if model is None:
        model = get_gemini_client()

    chat = model.start_chat(history=messages[:-1] if len(messages) > 1 else [])
    last_message = messages[-1]["parts"][0] if messages else ""

    response = chat.send_message(last_message, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text


def chat_once(user_message: str, history: list[dict] | None = None) -> str:
    """Non-streaming single response. Returns full text."""
    model = get_gemini_client()
    hist = history or []
    chat = model.start_chat(history=hist)
    response = chat.send_message(user_message)
    return response.text
