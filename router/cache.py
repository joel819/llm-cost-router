"""Persistent response cache keyed by hash(normalised prompt + task type)."""
from __future__ import annotations

import hashlib
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path


def normalise(prompt: str) -> str:
    """Unicode-normalise and collapse whitespace. Case is kept: it can change meaning."""
    return " ".join(unicodedata.normalize("NFKC", prompt).split())


def cache_key(prompt: str, task: str) -> str:
    return hashlib.sha256(f"{task}\n{normalise(prompt)}".encode()).hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    text: str
    tier: str
    model: str


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, task TEXT NOT NULL, text TEXT NOT NULL,
            tier TEXT NOT NULL, model TEXT NOT NULL, created REAL NOT NULL, hits INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, task TEXT NOT NULL,
            key TEXT NOT NULL, tier TEXT, model TEXT, cached INTEGER NOT NULL, passed INTEGER NOT NULL,
            attempts TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
            cost REAL, cost_note TEXT, latency_ms INTEGER NOT NULL);
    """)
    return conn


class Cache:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, key: str) -> CacheEntry | None:
        r = self.conn.execute("SELECT text, tier, model FROM cache WHERE key = ?", (key,)).fetchone()
        if not r:
            return None
        self.conn.execute("UPDATE cache SET hits = hits + 1 WHERE key = ?", (key,))
        self.conn.commit()
        return CacheEntry(r["text"], r["tier"], r["model"])

    def put(self, key: str, task: str, entry: CacheEntry) -> None:
        self.conn.execute("INSERT OR REPLACE INTO cache (key, task, text, tier, model, created) VALUES (?,?,?,?,?,?)",
                          (key, task, entry.text, entry.tier, entry.model, time.time()))
        self.conn.commit()
