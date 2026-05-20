from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from threading import Lock
from uuid import uuid4


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, session_id, role, content, datetime.now(timezone.utc).isoformat()),
            )

    def log_event(self, session_id: str, kind: str, payload: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO events (id, session_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, session_id, kind, json.dumps(payload, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
            )

    def recent_messages(self, session_id: str, limit: int = 12) -> list[dict[str, str]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [
            {"role": role, "content": content, "created_at": created_at}
            for role, content, created_at in reversed(rows)
        ]
