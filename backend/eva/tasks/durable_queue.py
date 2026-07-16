"""Durable task queue — work that survives a crash or reboot (Phase 45).

Until now an agent task lived and died inside one HTTP request: Eva awaited
``run_agentic_task`` inline, and if the process was killed mid-run (crash,
reboot, power loss) the work simply vanished. There was no persistent record of
"things to do" that outlives the process. That is the floor Phase 46
(proactivity) has to stand on, so it comes first.

This module is that floor: a small SQLite-backed queue with an explicit
lifecycle and — the point of the whole exercise — **crash recovery on startup**.

Lifecycle::

    queued ──claim──> running ──complete──> succeeded
       ^                  │
       │                  ├──fail (attempts left)──> queued   (retry)
       │                  └──fail (no attempts)────> failed
       └──recover_orphans (a 'running' task after restart)

The load-bearing safety invariant: **the queue persists a REQUEST, never an
approval.** Recovering and re-running a task sends it back through the very same
permission gate and confirmation ledger it faced the first time — a task that
needed confirmation still needs confirmation. Durability must never become a
back door that replays a privileged action unattended. (Draining the queue is a
separate, opt-in worker; see :mod:`eva.tasks.worker`.)

Thread-safe and fail-safe. Pure storage/state-machine — it executes nothing
itself, so it cannot bypass any gate.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
CANCELLED = "cancelled"

TERMINAL_STATES = frozenset({SUCCEEDED, FAILED, CANCELLED})
ACTIVE_STATES = frozenset({QUEUED, RUNNING})

_DEFAULT_MAX_ATTEMPTS = 3
_MAX_REQUEST_LEN = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DurableTask:
    id: str
    request: str
    status: str
    attempts: int
    max_attempts: int
    priority: int
    source: str
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
    result_summary: str
    error: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_COLUMNS = (
    "id, request, status, attempts, max_attempts, priority, source, "
    "created_at, updated_at, started_at, finished_at, result_summary, error"
)


def _row_to_task(row: tuple) -> DurableTask:
    return DurableTask(
        id=row[0],
        request=row[1],
        status=row[2],
        attempts=int(row[3]),
        max_attempts=int(row[4]),
        priority=int(row[5]),
        source=row[6],
        created_at=row[7],
        updated_at=row[8],
        started_at=row[9],
        finished_at=row[10],
        result_summary=row[11] or "",
        error=row[12] or "",
    )


class DurableTaskQueue:
    """A crash-safe, SQLite-backed queue of agent task requests."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # Connections are always closed by the caller (via contextlib.closing):
        # sqlite3's own context manager commits but does NOT close, which would
        # leak handles and hold locks against other instances on the same file.
        return sqlite3.connect(self.path, timeout=10.0)

    def _fetch(self, conn: sqlite3.Connection, task_id: str) -> DurableTask | None:
        """Read a task on an EXISTING connection.

        Used by the mutating methods so they never call the public ``get`` (which
        takes ``self._lock``) while already holding that lock — ``Lock`` is not
        reentrant, so doing so would deadlock."""
        row = conn.execute(f"SELECT {_COLUMNS} FROM durable_tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None

    def _init_db(self) -> None:
        with self._lock, closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS durable_tasks (
                    id TEXT PRIMARY KEY,
                    request TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    result_summary TEXT,
                    error TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_durable_tasks_status ON durable_tasks(status, priority DESC, created_at)")

    # -- enqueue --------------------------------------------------------------

    def enqueue(
        self,
        request: str,
        *,
        source: str = "user",
        priority: int = 0,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    ) -> DurableTask | None:
        """Add a new task in the ``queued`` state. Returns it, or ``None`` if the
        request was empty. Never raises."""
        try:
            text = " ".join(str(request or "").split())[:_MAX_REQUEST_LEN].strip()
            if not text:
                return None
            now = _now()
            task = DurableTask(
                id=uuid4().hex,
                request=text,
                status=QUEUED,
                attempts=0,
                max_attempts=max(1, int(max_attempts)),
                priority=int(priority),
                source=str(source or "user")[:60],
                created_at=now,
                updated_at=now,
                started_at=None,
                finished_at=None,
                result_summary="",
                error="",
            )
            with self._lock, closing(self._connect()) as conn, conn:
                conn.execute(
                    f"INSERT INTO durable_tasks ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        task.id, task.request, task.status, task.attempts, task.max_attempts, task.priority,
                        task.source, task.created_at, task.updated_at, task.started_at, task.finished_at,
                        task.result_summary, task.error,
                    ),
                )
            return task
        except Exception:
            return None

    # -- claim / transitions --------------------------------------------------

    def claim(self) -> DurableTask | None:
        """Atomically claim the next queued task and mark it ``running``.

        Highest priority first, then oldest. Uses an IMMEDIATE transaction so two
        workers can never claim the same task. Returns ``None`` if nothing is
        queued. Never raises."""
        try:
            with self._lock, closing(self._connect()) as conn:
                conn.isolation_level = None  # manual transaction control
                conn.execute("BEGIN IMMEDIATE")
                try:
                    row = conn.execute(
                        f"SELECT {_COLUMNS} FROM durable_tasks WHERE status = ? "
                        "ORDER BY priority DESC, created_at ASC LIMIT 1",
                        (QUEUED,),
                    ).fetchone()
                    if row is None:
                        conn.execute("COMMIT")
                        return None
                    task = _row_to_task(row)
                    now = _now()
                    conn.execute(
                        "UPDATE durable_tasks SET status = ?, attempts = ?, started_at = ?, updated_at = ? WHERE id = ?",
                        (RUNNING, task.attempts + 1, now, now, task.id),
                    )
                    claimed = self._fetch(conn, task.id)
                    conn.execute("COMMIT")
                    return claimed
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        except Exception:
            return None

    def complete(self, task_id: str, summary: str = "") -> DurableTask | None:
        """Mark a running task ``succeeded``."""
        return self._finish(task_id, SUCCEEDED, summary=summary)

    def fail(self, task_id: str, error: str = "") -> DurableTask | None:
        """Fail a running task: retry (back to ``queued``) if attempts remain,
        otherwise mark ``failed``."""
        try:
            with self._lock, closing(self._connect()) as conn, conn:
                task = self._fetch(conn, task_id)
                if task is None:
                    return None
                if task.status in TERMINAL_STATES:
                    return task
                now = _now()
                if task.attempts < task.max_attempts:
                    conn.execute(
                        "UPDATE durable_tasks SET status = ?, updated_at = ?, started_at = NULL, error = ? WHERE id = ?",
                        (QUEUED, now, str(error or "")[:500], task_id),
                    )
                else:
                    conn.execute(
                        "UPDATE durable_tasks SET status = ?, updated_at = ?, finished_at = ?, error = ? WHERE id = ?",
                        (FAILED, now, now, str(error or "")[:500], task_id),
                    )
                return self._fetch(conn, task_id)
        except Exception:
            return None

    def cancel(self, task_id: str) -> DurableTask | None:
        """Cancel a task that has not reached a terminal state."""
        try:
            with self._lock, closing(self._connect()) as conn, conn:
                task = self._fetch(conn, task_id)
                if task is None or task.status in TERMINAL_STATES:
                    return task
                now = _now()
                conn.execute(
                    "UPDATE durable_tasks SET status = ?, updated_at = ?, finished_at = ? WHERE id = ?",
                    (CANCELLED, now, now, task_id),
                )
                return self._fetch(conn, task_id)
        except Exception:
            return None

    def _finish(self, task_id: str, status: str, *, summary: str = "") -> DurableTask | None:
        try:
            with self._lock, closing(self._connect()) as conn, conn:
                task = self._fetch(conn, task_id)
                if task is None or task.status in TERMINAL_STATES:
                    return task
                now = _now()
                conn.execute(
                    "UPDATE durable_tasks SET status = ?, updated_at = ?, finished_at = ?, result_summary = ? WHERE id = ?",
                    (status, now, now, str(summary or "")[:1000], task_id),
                )
                return self._fetch(conn, task_id)
        except Exception:
            return None

    # -- crash recovery -------------------------------------------------------

    def recover_orphans(self) -> dict[str, Any]:
        """Resume after a crash/reboot: reconcile tasks left mid-flight.

        A task still marked ``running`` when the process starts is an orphan — it
        was executing when Eva died. Each is either re-queued for another attempt
        (if attempts remain) or abandoned as ``failed`` (so a task that crashes
        Eva can't wedge her in an infinite restart→crash loop). Returns a summary.

        Re-queuing only restores the *request*; the re-run faces the gate again,
        so no privileged action is ever silently replayed."""
        recovered = 0
        abandoned = 0
        try:
            with self._lock, closing(self._connect()) as conn, conn:
                rows = conn.execute(f"SELECT {_COLUMNS} FROM durable_tasks WHERE status = ?", (RUNNING,)).fetchall()
                now = _now()
                for row in rows:
                    task = _row_to_task(row)
                    if task.attempts < task.max_attempts:
                        conn.execute(
                            "UPDATE durable_tasks SET status = ?, updated_at = ?, started_at = NULL, "
                            "error = ? WHERE id = ?",
                            (QUEUED, now, "recovered after interruption (crash/restart)", task.id),
                        )
                        recovered += 1
                    else:
                        conn.execute(
                            "UPDATE durable_tasks SET status = ?, updated_at = ?, finished_at = ?, "
                            "error = ? WHERE id = ?",
                            (FAILED, now, now, "abandoned after repeated interruption", task.id),
                        )
                        abandoned += 1
        except Exception:
            pass
        return {"recovered": recovered, "abandoned": abandoned}

    # -- reads ----------------------------------------------------------------

    def get(self, task_id: str) -> DurableTask | None:
        try:
            with self._lock, closing(self._connect()) as conn:
                return self._fetch(conn, task_id)
        except Exception:
            return None

    def list_tasks(self, *, status: str | None = None, limit: int = 50) -> list[DurableTask]:
        try:
            with self._lock, closing(self._connect()) as conn:
                if status:
                    rows = conn.execute(
                        f"SELECT {_COLUMNS} FROM durable_tasks WHERE status = ? "
                        "ORDER BY priority DESC, created_at ASC LIMIT ?",
                        (status, int(limit)),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        f"SELECT {_COLUMNS} FROM durable_tasks ORDER BY created_at DESC LIMIT ?",
                        (int(limit),),
                    ).fetchall()
            return [_row_to_task(row) for row in rows]
        except Exception:
            return []

    def stats(self) -> dict[str, int]:
        """Counts per lifecycle state (plus ``total``). Fail-safe to zeros."""
        base = {QUEUED: 0, RUNNING: 0, SUCCEEDED: 0, FAILED: 0, CANCELLED: 0}
        try:
            with self._lock, closing(self._connect()) as conn:
                for status, count in conn.execute("SELECT status, COUNT(*) FROM durable_tasks GROUP BY status").fetchall():
                    if status in base:
                        base[status] = int(count)
        except Exception:
            pass
        base["total"] = sum(base.values())
        return base


__all__ = [
    "DurableTaskQueue",
    "DurableTask",
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
]
