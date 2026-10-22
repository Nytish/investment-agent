"""
tests/test_agent.py — Unit tests for the APEX agent layer.

No real LLM calls — all providers mocked.
No real network — requests mocked via unittest.mock.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Model Router ─────────────────────────────────────────────────────────────

class TestOllamaProvider:
    def test_available_false_when_connection_refused(self):
        from agent.model_router import OllamaProvider
        provider = OllamaProvider(base_url="http://127.0.0.1:19999")  # nothing there
        # Should return False gracefully, not raise
        result = provider.available()
        assert result is False

    def test_available_false_when_model_not_in_list(self):
        from agent.model_router import OllamaProvider
        provider = OllamaProvider(model="qwen3:8b", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama3:8b"}]}
        mock_response.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_response):
            assert provider.available() is False

    def test_available_true_when_model_present(self):
        from agent.model_router import OllamaProvider
        provider = OllamaProvider(model="qwen3:8b")
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "qwen3:8b"}]}
        mock_response.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_response):
            assert provider.available() is True

    def test_available_false_on_exception(self):
        from agent.model_router import OllamaProvider
        provider = OllamaProvider()
        with patch("requests.get", side_effect=ConnectionError("refused")):
            assert provider.available() is False

    def test_name_includes_model(self):
        from agent.model_router import OllamaProvider
        p = OllamaProvider(model="qwen3:8b")
        assert "qwen3:8b" in p.name

    def test_complete_returns_content(self):
        from agent.model_router import OllamaProvider
        provider = OllamaProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Hello Nitish!"}}
        mock_response.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_response):
            result = provider.complete([{"role": "user", "content": "hi"}])
        assert result == "Hello Nitish!"


class TestGeminiProvider:
    def test_available_false_without_env_var(self, monkeypatch):
        from agent.model_router import GeminiProvider
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = GeminiProvider()
        assert provider.available() is False

    def test_available_true_with_env_var(self, monkeypatch):
        from agent.model_router import GeminiProvider
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        provider = GeminiProvider()
        assert provider.available() is True

    def test_name_includes_model(self):
        from agent.model_router import GeminiProvider
        p = GeminiProvider(model="gemini-2.5-flash")
        assert "gemini-2.5-flash" in p.name

    def test_complete_returns_text(self, monkeypatch):
        from agent.model_router import GeminiProvider
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        provider = GeminiProvider()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Buy VWCE."}]}}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_response):
            result = provider.complete([
                {"role": "system", "content": "You are APEX."},
                {"role": "user", "content": "What should I invest in?"},
            ])
        assert result == "Buy VWCE."


class TestModelRouter:
    def test_raises_when_no_providers_available(self):
        from agent.model_router import ModelRouter, OllamaProvider, GeminiProvider
        # All providers unavailable
        p1 = MagicMock(spec=OllamaProvider)
        p1.available.return_value = False
        p1.name = "mock1"
        p2 = MagicMock(spec=GeminiProvider)
        p2.available.return_value = False
        p2.name = "mock2"
        router = ModelRouter(providers=[p1, p2])
        with pytest.raises(RuntimeError, match="No LLM provider available"):
            router.route([{"role": "user", "content": "hello"}])

    def test_uses_first_available_provider(self):
        from agent.model_router import ModelRouter
        p1 = MagicMock()
        p1.available.return_value = False
        p1.name = "unavailable"
        p2 = MagicMock()
        p2.available.return_value = True
        p2.complete.return_value = "response from p2"
        p2.name = "available"
        router = ModelRouter(providers=[p1, p2])
        response, name = router.route([{"role": "user", "content": "test"}])
        assert response == "response from p2"
        assert name == "available"
        p1.complete.assert_not_called()

    def test_falls_back_on_provider_exception(self):
        from agent.model_router import ModelRouter
        p1 = MagicMock()
        p1.available.return_value = True
        p1.complete.side_effect = RuntimeError("timeout")
        p1.name = "failing"
        p2 = MagicMock()
        p2.available.return_value = True
        p2.complete.return_value = "fallback response"
        p2.name = "fallback"
        router = ModelRouter(providers=[p1, p2])
        response, name = router.route([{"role": "user", "content": "test"}])
        assert response == "fallback response"
        assert name == "fallback"


# ── System Prompt ─────────────────────────────────────────────────────────────

class TestSystemPrompt:
    def test_contains_nitish(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({})
        assert "Nitish" in prompt

    def test_contains_fsa_amount(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({"sparer_pauschbetrag_eur": 2000})
        assert "2,000" in prompt or "2000" in prompt

    def test_contains_vwce(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({})
        assert "VWCE" in prompt

    def test_flags_steuererklarung_overdue(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({"steuererklarung_2024": "NOT FILED — action required"})
        assert "NOT FILED" in prompt or "STEUERERKLÄRUNG" in prompt.upper()

    def test_market_snapshot_included_when_provided(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({}, market_snapshot="VWCE: €112.50")
        assert "€112.50" in prompt

    def test_uses_profile_savings(self):
        from agent.system_prompt import build_system_prompt
        prompt = build_system_prompt({"savings_scalable_eur": 50000})
        assert "50,000" in prompt


# ── Conversation ──────────────────────────────────────────────────────────────

class TestConversation:
    def test_save_and_load_roundtrip(self, tmp_path):
        from agent.conversation import init_db, save_turn, load_history
        db = tmp_path / "test_conv.db"
        init_db(db_path=db)
        sid = str(uuid.uuid4())
        save_turn(sid, "user", "Hello APEX", db_path=db)
        save_turn(sid, "assistant", "Hello Nitish", db_path=db)
        history = load_history(sid, db_path=db)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello APEX"}
        assert history[1] == {"role": "assistant", "content": "Hello Nitish"}

    def test_load_history_respects_max_turns(self, tmp_path):
        from agent.conversation import init_db, save_turn, load_history
        db = tmp_path / "test_conv.db"
        init_db(db_path=db)
        sid = str(uuid.uuid4())
        for i in range(20):
            save_turn(sid, "user", f"msg {i}", db_path=db)
        history = load_history(sid, max_turns=5, db_path=db)
        assert len(history) == 5
        # Should be the LAST 5 in chronological order
        assert history[-1]["content"] == "msg 19"

    def test_load_history_empty_for_unknown_session(self, tmp_path):
        from agent.conversation import init_db, load_history
        db = tmp_path / "test_conv.db"
        init_db(db_path=db)
        result = load_history("nonexistent-session-id", db_path=db)
        assert result == []

    def test_load_history_returns_empty_when_db_missing(self, tmp_path):
        from agent.conversation import load_history
        db = tmp_path / "does_not_exist.db"
        result = load_history("any-session", db_path=db)
        assert result == []

    def test_messages_are_chronological(self, tmp_path):
        from agent.conversation import init_db, save_turn, load_history
        db = tmp_path / "test_conv.db"
        init_db(db_path=db)
        sid = str(uuid.uuid4())
        save_turn(sid, "user", "first", db_path=db)
        save_turn(sid, "assistant", "second", db_path=db)
        save_turn(sid, "user", "third", db_path=db)
        history = load_history(sid, db_path=db)
        assert [m["content"] for m in history] == ["first", "second", "third"]

    def test_sessions_are_isolated(self, tmp_path):
        from agent.conversation import init_db, save_turn, load_history
        db = tmp_path / "test_conv.db"
        init_db(db_path=db)
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        save_turn(sid1, "user", "session 1 msg", db_path=db)
        save_turn(sid2, "user", "session 2 msg", db_path=db)
        h1 = load_history(sid1, db_path=db)
        h2 = load_history(sid2, db_path=db)
        assert len(h1) == 1 and h1[0]["content"] == "session 1 msg"
        assert len(h2) == 1 and h2[0]["content"] == "session 2 msg"
