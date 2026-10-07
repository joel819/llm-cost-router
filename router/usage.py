"""Per-request usage log (SQLite) and a summary over it."""
from __future__ import annotations

import json
import sqlite3
import time


def log_request(conn: sqlite3.Connection, *, task: str, key: str, tier: str | None, model: str | None, cached: bool,
                passed: bool, attempts: list[dict], input_tokens: int, output_tokens: int, cost: float | None,
                cost_note: str | None, latency_ms: int) -> None:
    conn.execute("INSERT INTO requests (ts, task, key, tier, model, cached, passed, attempts, input_tokens, output_tokens,"
                 " cost, cost_note, latency_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (time.time(), task, key, tier, model, int(cached), int(passed), json.dumps(attempts), input_tokens,
                  output_tokens, cost, cost_note, latency_ms))
    conn.commit()


def summary(conn: sqlite3.Connection) -> dict:
    r = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(cached),0) hits, COALESCE(SUM(input_tokens),0) i, "
                     "COALESCE(SUM(output_tokens),0) o, SUM(cost) cost, SUM(cost IS NULL AND cached = 0) unpriced "
                     "FROM requests").fetchone()
    by_tier = {row["tier"] or "(cache)": row["n"] for row in conn.execute(
        "SELECT tier, COUNT(*) n FROM requests WHERE cached = 0 GROUP BY tier")}
    return {"requests": r["n"], "cache_hits": r["hits"], "input_tokens": r["i"], "output_tokens": r["o"],
            "cost_usd": r["cost"] if not r["unpriced"] else None, "requests_without_price": r["unpriced"] or 0,
            "final_tier_counts": by_tier}
