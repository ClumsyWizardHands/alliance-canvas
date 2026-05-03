"""
SQLite persistence for conversations, messages, tool calls, and cards.

Single-writer, single-reader (the FastAPI process). No connection pool needed
for v1 — open a connection per call, close it. WAL mode keeps reads non-blocking
during writes.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import SQLITE_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace    TEXT    NOT NULL,
    title        TEXT    NOT NULL DEFAULT '',
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    role            TEXT    NOT NULL,
    agent           TEXT,
    content         TEXT    NOT NULL DEFAULT '',
    tool_calls_json TEXT,
    tool_call_id    TEXT,
    tool_name       TEXT,
    created_at      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, sequence);

CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id  INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    card_type   TEXT    NOT NULL,
    data_json   TEXT    NOT NULL,
    sequence    INTEGER NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_message ON cards(message_id, sequence);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def now() -> int:
    return int(time.time() * 1000)


def create_conversation(workspace: str, title: str = "") -> int:
    ts = now()
    with connect() as c:
        cur = c.execute(
            "INSERT INTO conversations(workspace, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (workspace, title, ts, ts),
        )
        return int(cur.lastrowid)


def list_conversations(workspace: str | None = None, limit: int = 50) -> list[dict]:
    with connect() as c:
        if workspace:
            rows = c.execute(
                "SELECT * FROM conversations WHERE workspace = ? ORDER BY updated_at DESC LIMIT ?",
                (workspace, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def list_messages(conversation_id: int) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY sequence ASC",
            (conversation_id,),
        ).fetchall()
        msgs = []
        for r in rows:
            d = dict(r)
            if d.get("tool_calls_json"):
                d["tool_calls"] = json.loads(d["tool_calls_json"])
            cards = c.execute(
                "SELECT card_type, data_json, sequence FROM cards WHERE message_id = ? ORDER BY sequence ASC",
                (d["id"],),
            ).fetchall()
            d["cards"] = [
                {"card_type": cc["card_type"], "data": json.loads(cc["data_json"]), "sequence": cc["sequence"]}
                for cc in cards
            ]
            msgs.append(d)
        return msgs


def append_message(
    conversation_id: int,
    role: str,
    content: str = "",
    agent: str | None = None,
    tool_calls: list[dict] | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> int:
    with connect() as c:
        seq_row = c.execute(
            "SELECT COALESCE(MAX(sequence), -1) + 1 AS next FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        seq = int(seq_row["next"])
        cur = c.execute(
            """INSERT INTO messages
               (conversation_id, sequence, role, agent, content, tool_calls_json,
                tool_call_id, tool_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conversation_id, seq, role, agent, content,
                json.dumps(tool_calls) if tool_calls else None,
                tool_call_id, tool_name, now(),
            ),
        )
        c.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now(), conversation_id),
        )
        return int(cur.lastrowid)


def append_card(message_id: int, card_type: str, data: dict[str, Any]) -> int:
    with connect() as c:
        seq_row = c.execute(
            "SELECT COALESCE(MAX(sequence), -1) + 1 AS next FROM cards WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        seq = int(seq_row["next"])
        cur = c.execute(
            "INSERT INTO cards(message_id, card_type, data_json, sequence, created_at) VALUES (?, ?, ?, ?, ?)",
            (message_id, card_type, json.dumps(data), seq, now()),
        )
        return int(cur.lastrowid)


def update_message_content(message_id: int, content: str) -> None:
    with connect() as c:
        c.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))


def update_conversation_title(conversation_id: int, title: str) -> None:
    with connect() as c:
        c.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now(), conversation_id),
        )
