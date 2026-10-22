"""
conversation.py — SQLite-backed conversation history for APEX agent.

Replaces Firebase Firestore with a local DB. Cross-session persistent.
Stored at data/conversations.db (gitignored).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Relative to this file: apex2/agent/../data/conversations.db
DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"


def init_db(db_path: Path | None = None) -> None:
    """Create conversations table if it doesn't exist."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role      TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content   TEXT NOT NULL,
                ts        TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON conversations (session_id, id)"
        )
        conn.commit()


def save_turn(session_id: str, role: str, content: str, db_path: Path | None = None) -> None:
    """Persist one conversation turn."""
    path = db_path or DB_PATH
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()


def load_history(
    session_id: str,
    max_turns: int = 10,
    db_path: Path | None = None,
) -> list[dict]:
    """
    Load the last max_turns messages for a session, in chronological order.
    Returns [] if session is unknown or DB doesn't exist yet.
    """
    path = db_path or DB_PATH
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM conversations
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, max_turns),
        ).fetchall()
    # Reverse so messages are oldest-first (chronological for the LLM)
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_session(session_id: str, db_path: Path | None = None) -> int:
    """Delete all turns for a session. Returns number of rows deleted."""
    path = db_path or DB_PATH
    if not path.exists():
        return 0
    with sqlite3.connect(path) as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE session_id = ?", (session_id,)
        )
        conn.commit()
        return cursor.rowcount


def list_sessions(db_path: Path | None = None) -> list[dict]:
    """List all sessions with turn count and last message time."""
    path = db_path or DB_PATH
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT session_id, COUNT(*) as turns, MAX(ts) as last_ts
            FROM conversations
            GROUP BY session_id
            ORDER BY last_ts DESC
            """
        ).fetchall()
    return [
        {"session_id": sid, "turns": turns, "last_ts": ts}
        for sid, turns, ts in rows
    ]
