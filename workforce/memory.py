"""SQLite-backed long-term memory and run log for the workforce."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    goal         TEXT NOT NULL,
    status       TEXT NOT NULL,
    provider     TEXT NOT NULL,
    model        TEXT NOT NULL,
    created_at   REAL NOT NULL,
    finished_at  REAL,
    report_path  TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    run_id     TEXT NOT NULL,
    task_id    TEXT NOT NULL,
    capability TEXT NOT NULL,
    title      TEXT NOT NULL,
    status     TEXT NOT NULL,
    attempt    INTEGER NOT NULL DEFAULT 1,
    input      TEXT,
    output     TEXT,
    verdict    TEXT,
    score      REAL,
    comments   TEXT,
    is_final   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, task_id)
);
CREATE TABLE IF NOT EXISTS messages (
    run_id     TEXT NOT NULL,
    task_id    TEXT,
    agent      TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    created_at REAL NOT NULL,
    ttl        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS artifacts (
    run_id     TEXT NOT NULL,
    path       TEXT NOT NULL,
    kind       TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_run ON tasks (run_id);
CREATE INDEX IF NOT EXISTS idx_messages_run ON messages (run_id, task_id);
"""


class Memory:
    """Thread-safe wrapper around a single SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------ runs
    def start_run(
        self,
        run_id: str,
        goal: str,
        provider: str,
        model: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, goal, status, provider, model, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, goal, "running", provider, model, time.time()),
            )
            self._conn.commit()

    def finish_run(self, run_id: str, status: str, report_path: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status = ?, finished_at = ?, report_path = ? WHERE run_id = ?",
                (status, time.time(), report_path, run_id),
            )
            self._conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------ tasks
    def upsert_task(
        self,
        run_id: str,
        task_id: str,
        capability: str,
        title: str,
        *,
        status: str = "pending",
        attempt: int = 1,
        input_: str | None = None,
        output: str | None = None,
        verdict: str | None = None,
        score: float | None = None,
        comments: str | None = None,
        is_final: bool = False,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO tasks "
                "(run_id, task_id, capability, title, status, attempt, input, output, "
                "verdict, score, comments, is_final) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id, task_id, capability, title, status, attempt, input_,
                    output, verdict, score, comments, int(is_final),
                ),
            )
            self._conn.commit()

    def get_tasks(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE run_id = ? ORDER BY rowid", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------ messages
    def log_message(self, run_id: str, agent: str, role: str, content: str, task_id: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages (run_id, task_id, agent, role, content, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (run_id, task_id, agent, role, content, time.time()),
            )
            self._conn.commit()

    def get_messages(self, run_id: str, task_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if task_id:
                rows = self._conn.execute(
                    "SELECT * FROM messages WHERE run_id = ? AND task_id = ? ORDER BY rowid",
                    (run_id, task_id),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM messages WHERE run_id = ? ORDER BY rowid", (run_id,)
                ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------ facts (long-term memory)
    def remember(self, key: str, value: Any, ttl: int = 0) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO facts (key, value, created_at, ttl) VALUES (?,?,?,?)",
                (key, json.dumps(value), time.time(), int(ttl)),
            )
            self._conn.commit()

    def recall(self, key: str) -> Any | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM facts WHERE key = ?", (key,)
            ).fetchone()
            now = time.time()
            if row and row["ttl"] and now - row["created_at"] > row["ttl"]:
                self._conn.execute("DELETE FROM facts WHERE key = ?", (key,))
                self._conn.commit()
                return None
        if not row:
            return None
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    def forget_old(self) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM facts WHERE ttl > 0 AND created_at + ttl < ?", (time.time(),)
            )
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------ artifacts
    def add_artifact(self, run_id: str, path: str, kind: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO artifacts (run_id, path, kind, created_at) VALUES (?,?,?,?)",
                (run_id, path, kind, time.time()),
            )
            self._conn.commit()

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM artifacts WHERE run_id = ? ORDER BY rowid", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
