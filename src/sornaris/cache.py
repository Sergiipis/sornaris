"""SQLite-backed score cache for bisect runs."""

from __future__ import annotations

import sqlite3
from typing import Optional


def make_cache_key(prompt_hash: str, model_id: str, example_id: str) -> str:
    return f"{prompt_hash}|{model_id}|{example_id}"


class BisectCache:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS bisect_cache (key TEXT PRIMARY KEY, value REAL NOT NULL)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[float]:
        cur = self._conn.execute("SELECT value FROM bisect_cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if row is None:
            return None
        return float(row[0])

    def set(self, key: str, value: float) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO bisect_cache (key, value) VALUES (?, ?)",
            (key, float(value)),
        )
        self._conn.commit()

    def has(self, key: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM bisect_cache WHERE key = ? LIMIT 1", (key,))
        return cur.fetchone() is not None

    def clear(self) -> None:
        self._conn.execute("DELETE FROM bisect_cache")
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.ProgrammingError:
            pass

    def __enter__(self) -> "BisectCache":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
