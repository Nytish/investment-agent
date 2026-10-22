"""
journal.py — APEX 2.0
Append-only local decision journal using SQLite.
All data stays local. No network. No cloud sync.
"""
from __future__ import annotations
import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent / "data" / "apex_journal.db"


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialise(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist."""
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,          -- ISO 8601 UTC
                run_id      TEXT,
                asset       TEXT,
                action      TEXT NOT NULL,          -- BUY / HOLD / REDUCE / NO_ACTION / NOTE
                rationale   TEXT,
                policy_verdict TEXT,
                metadata    TEXT,                   -- JSON blob for structured data
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL,
                question   TEXT NOT NULL,
                answered   INTEGER NOT NULL DEFAULT 0,  -- 0=open 1=answered
                answer     TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


def log_decision(
    action: str,
    rationale: str,
    asset: Optional[str] = None,
    run_id: Optional[str] = None,
    policy_verdict: Optional[str] = None,
    metadata: Optional[dict] = None,
    db_path: Path = DB_PATH,
) -> int:
    """Append a decision to the journal. Returns the new row id."""
    initialise(db_path)
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO decisions (ts, run_id, asset, action, rationale, policy_verdict, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, run_id, asset, action.upper(), rationale, policy_verdict,
             json.dumps(metadata) if metadata else None),
        )
        return cur.lastrowid


def log_open_question(question: str, db_path: Path = DB_PATH) -> int:
    """Log a question awaiting human input."""
    initialise(db_path)
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO questions (ts, question) VALUES (?, ?)", (ts, question)
        )
        return cur.lastrowid


def answer_question(question_id: int, answer: str, db_path: Path = DB_PATH) -> None:
    initialise(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE questions SET answered=1, answer=? WHERE id=?",
            (answer, question_id),
        )


def get_open_questions(db_path: Path = DB_PATH) -> list[dict]:
    initialise(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, ts, question FROM questions WHERE answered=0 ORDER BY ts"
        ).fetchall()
    return [{"id": r[0], "ts": r[1], "question": r[2]} for r in rows]


def get_recent_decisions(limit: int = 10, db_path: Path = DB_PATH) -> list[dict]:
    initialise(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, ts, asset, action, rationale, policy_verdict "
            "FROM decisions ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {"id": r[0], "ts": r[1], "asset": r[2], "action": r[3],
         "rationale": r[4], "policy_verdict": r[5]}
        for r in rows
    ]
