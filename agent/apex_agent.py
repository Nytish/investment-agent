"""
apex_agent.py — APEX investment mentor agent entry point.

Usage (CLI):
    python -m agent.apex_agent

Usage (Python):
    from agent.apex_agent import chat
    reply = chat("Should I start with VWCE or IWDA?", session_id="my-session")
"""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from agent.conversation import init_db, load_history, save_turn
from agent.model_router import ModelRouter
from agent.system_prompt import build_system_prompt

_PROFILE_PATH = Path(__file__).parent.parent / "data" / "financial_profile.yaml"


def _load_profile() -> dict:
    """Load financial profile from YAML. Returns empty dict if not found."""
    if _PROFILE_PATH.exists():
        with open(_PROFILE_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def _build_market_snapshot() -> str:
    """
    Try to get a live market snapshot from MarketCache.
    Falls back to a static message if cache is empty or unavailable.
    """
    try:
        from core.market_feed import MarketCache, ETF_TICKERS
        cache = MarketCache()
        lines = []
        for name, ticker in ETF_TICKERS.items():
            try:
                price = cache.get_latest(ticker)
                if price is not None:
                    lines.append(f"  {name} ({ticker}): €{price:,.2f}")
            except Exception:
                pass
        if lines:
            return "ETF prices (cached):\n" + "\n".join(lines)
    except Exception:
        pass
    return "Market data not available — run `python core/market_feed.py` to populate cache."


def chat(
    user_message: str,
    session_id: str | None = None,
    router: ModelRouter | None = None,
    max_history: int = 10,
) -> str:
    """
    Single conversation turn. Call repeatedly with the same session_id for multi-turn.

    Args:
        user_message: the user's input text
        session_id:   persistent session identifier (UUID string). Auto-generated if None.
        router:       ModelRouter instance (injectable for testing)
        max_history:  how many previous turns to include in context

    Returns:
        The assistant's response text.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    init_db()
    history = load_history(session_id, max_turns=max_history)

    profile = _load_profile()
    market_snapshot = _build_market_snapshot()

    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt(profile, market_snapshot)},
        *history,
        {"role": "user", "content": user_message},
    ]

    if router is None:
        router = ModelRouter()

    response, provider_name = router.route(messages)

    save_turn(session_id, "user", user_message)
    save_turn(session_id, "assistant", response)

    return response


def _repl() -> None:
    """Interactive CLI for chatting with APEX."""
    session_id = str(uuid.uuid4())
    router = ModelRouter()

    print("=" * 60)
    print("APEX — Personal Investment Mentor")
    print(f"Session: {session_id[:8]}  |  type 'quit' to exit")
    print("=" * 60)

    # Show which provider will be used
    for provider in router.providers:
        if provider.available():
            print(f"LLM: {provider.name}")
            break
    else:
        print("⚠️  No LLM available — set GEMINI_API_KEY or start Ollama")
        return

    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q", "bye"):
            print("Goodbye.")
            break

        try:
            reply = chat(user_input, session_id=session_id, router=router)
            print(f"\nAPEX: {reply}\n")
        except RuntimeError as e:
            print(f"\n⚠️  {e}\n")
            break


if __name__ == "__main__":
    _repl()
