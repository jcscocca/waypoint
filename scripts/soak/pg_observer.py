#!/usr/bin/env python3
"""Postgres observer for Waypoint's soak test (H2).

Samples pg_stat_activity / pg_stat_database / pg_locks on an interval and diffs
pg_stat_statements over the run. Shells `docker compose exec db psql --csv` so the
host needs no psycopg — only Python 3. Pair with scripts/soak/soak_driver.py.

    python scripts/soak/pg_observer.py --interval 15 --out soak-out

See docs/soak-testing.md for the full runbook.
"""
from __future__ import annotations

import csv
import io

# --------------------------------------------------------------------------- #
# Pure transforms (unit-tested; no subprocess)
# --------------------------------------------------------------------------- #


def parse_psql_csv(raw: str, columns: list[str]) -> list[dict[str, str]]:
    """Parse `psql --csv -t` output (no header) into dicts keyed by columns."""
    reader = csv.reader(io.StringIO(raw))
    rows = []
    for record in reader:
        if not record:
            continue
        rows.append({col: (record[i] if i < len(record) else "") for i, col in enumerate(columns)})
    return rows


def _f(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def activity_metrics(rows: list[dict]) -> dict:
    idle_txn_states = {"idle in transaction", "idle in transaction (aborted)"}
    active = [r for r in rows if r["state"] == "active"]
    idle_txn = [r for r in rows if r["state"] in idle_txn_states]
    return {
        "total": len(rows),
        "active": len(active),
        "idle": sum(1 for r in rows if r["state"] == "idle"),
        "idle_in_transaction": len(idle_txn),
        "waiting": sum(1 for r in active if r.get("wait_event_type")),
        "longest_query_age_s": max((_f(r["query_age"]) for r in active), default=0.0),
        "longest_idle_in_txn_s": max((_f(r["state_age"]) for r in idle_txn), default=0.0),
    }


def database_metrics(row: dict) -> dict:
    blks_read, blks_hit = _f(row["blks_read"]), _f(row["blks_hit"])
    total = blks_read + blks_hit
    return {
        "numbackends": int(_f(row["numbackends"])),
        "xact_commit": int(_f(row["xact_commit"])),
        "xact_rollback": int(_f(row["xact_rollback"])),
        "cache_hit_ratio": round(blks_hit / total, 4) if total else None,
        "deadlocks": int(_f(row["deadlocks"])),
        "temp_files": int(_f(row["temp_files"])),
        "temp_bytes": int(_f(row["temp_bytes"])),
    }


def lock_metrics(rows: list[dict]) -> dict:
    by_mode: dict[str, int] = {}
    not_granted = 0
    for r in rows:
        by_mode[r["mode"]] = by_mode.get(r["mode"], 0) + 1
        if r.get("granted") == "f":
            not_granted += 1
    return {"total": len(rows), "not_granted": not_granted, "by_mode": by_mode}


def statements_diff(start_rows: list[dict], end_rows: list[dict]) -> list[dict]:
    """Match statements by queryid; report mean-time growth over the run."""
    start_by_id = {r["queryid"]: r for r in start_rows}
    out = []
    for r in end_rows:
        s = start_by_id.get(r["queryid"])
        mean_start = _f(s["mean_exec_time"]) if s else 0.0
        mean_end = _f(r["mean_exec_time"])
        out.append({
            "queryid": r["queryid"],
            "query": r.get("query", "")[:200],
            "calls": int(_f(r.get("calls", "0"))),
            "mean_ms_start": mean_start,
            "mean_ms_end": mean_end,
            "mean_ratio": round(mean_end / mean_start, 2) if mean_start else None,
            "max_ms_end": _f(r.get("max_exec_time", "0")),
        })
    out.sort(key=lambda d: d["mean_ms_end"], reverse=True)
    return out
