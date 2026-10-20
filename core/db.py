from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import asyncpg  # type: ignore[import-untyped]


def clean_dsn(url: str) -> str:
    """Strip unsupported query parameters like sslmode and channel_binding for asyncpg."""
    if "?" in url:
        return url.split("?")[0]
    return url


async def get_connection(database_url: str) -> asyncpg.Connection:
    dsn = clean_dsn(database_url)
    return await asyncpg.connect(dsn, ssl="require")


async def init_db(database_url: str) -> None:
    """Initialize the preset_scenarios table in Neon tripagent database."""
    conn = await get_connection(database_url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS preset_scenarios (
                id VARCHAR(64) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                request_text TEXT NOT NULL,
                days INT NOT NULL,
                budget_eur NUMERIC(10, 2) NOT NULL,
                party_size INT NOT NULL,
                category VARCHAR(64) NOT NULL DEFAULT 'General',
                expected_feasibility VARCHAR(32) NOT NULL,
                total_cost NUMERIC(10, 2) DEFAULT 0.0,
                step_count INT DEFAULT 0,
                sse_events JSONB NOT NULL,
                plan_result JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_preset_req_text ON preset_scenarios (LOWER(request_text));
        """)
    finally:
        await conn.close()


async def save_presets(database_url: str, presets: list[dict[str, Any]]) -> None:
    """Upsert 20 preset scenarios into Neon database."""
    conn = await get_connection(database_url)
    try:
        for p in presets:
            await conn.execute(
                """
                INSERT INTO preset_scenarios (
                    id, title, request_text, days, budget_eur, party_size,
                    category, expected_feasibility, total_cost, step_count,
                    sse_events, plan_result
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    request_text = EXCLUDED.request_text,
                    days = EXCLUDED.days,
                    budget_eur = EXCLUDED.budget_eur,
                    party_size = EXCLUDED.party_size,
                    category = EXCLUDED.category,
                    expected_feasibility = EXCLUDED.expected_feasibility,
                    total_cost = EXCLUDED.total_cost,
                    step_count = EXCLUDED.step_count,
                    sse_events = EXCLUDED.sse_events,
                    plan_result = EXCLUDED.plan_result;
                """,
                p["id"],
                p["title"],
                p["request_text"],
                int(p["days"]),
                float(p["budget_eur"]),
                int(p["party_size"]),
                p.get("category", "General"),
                p.get("expected_feasibility", "feasible"),
                float(p.get("total_cost", 0.0)),
                int(p.get("step_count", 0)),
                json.dumps(p["sse_events"]),
                json.dumps(p.get("plan_result")),
            )
    finally:
        await conn.close()


async def get_all_presets_meta(database_url: str | None = None) -> list[dict[str, Any]]:
    """Retrieve metadata cards for all 20 presets. Falls back to local file if DB unavailable."""
    if database_url:
        try:
            conn = await get_connection(database_url)
            try:
                rows = await conn.fetch("""
                    SELECT id, title, request_text, days, budget_eur, party_size,
                           category, expected_feasibility, total_cost, step_count
                    FROM preset_scenarios
                    ORDER BY id ASC;
                """)
                if rows:
                    return [
                        {
                            "id": r["id"],
                            "title": r["title"],
                            "request_text": r["request_text"],
                            "days": r["days"],
                            "budget_eur": float(r["budget_eur"]),
                            "party_size": r["party_size"],
                            "category": r["category"],
                            "expected_feasibility": r["expected_feasibility"],
                            "total_cost": float(r["total_cost"]),
                            "step_count": r["step_count"],
                        }
                        for r in rows
                    ]
            finally:
                await conn.close()
        except (asyncpg.PostgresError, OSError, TimeoutError):
            pass  # Fallback to local cache

    # Fallback to data/preset_cache.json
    cache_path = Path("data/preset_cache.json")
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "request_text": item["request_text"],
                    "days": item["days"],
                    "budget_eur": float(item["budget_eur"]),
                    "party_size": item["party_size"],
                    "category": item.get("category", "General"),
                    "expected_feasibility": item.get("expected_feasibility", "feasible"),
                    "total_cost": float(item.get("total_cost", 0.0)),
                    "step_count": int(item.get("step_count", 0)),
                }
                for item in data
            ]
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    return []


async def get_preset_events(
    identifier: str, database_url: str | None = None
) -> list[dict[str, Any]] | None:
    """Find SSE events by preset ID or request text. Falls back to local file if DB unavailable."""
    ident_clean = identifier.strip().lower()

    if database_url:
        try:
            conn = await get_connection(database_url)
            try:
                row = await conn.fetchrow(
                    """
                    SELECT sse_events FROM preset_scenarios
                    WHERE LOWER(id) = $1 OR LOWER(request_text) = $1
                    LIMIT 1;
                    """,
                    ident_clean,
                )
                if row and row["sse_events"]:
                    events = row["sse_events"]
                    if isinstance(events, str):
                        return cast(list[dict[str, Any]], json.loads(events))
                    return cast(list[dict[str, Any]], events)
            finally:
                await conn.close()
        except (asyncpg.PostgresError, OSError, TimeoutError):
            pass

    # Fallback to data/preset_cache.json
    cache_path = Path("data/preset_cache.json")
    if cache_path.exists():
        try:
            items = json.loads(cache_path.read_text(encoding="utf-8"))
            for item in items:
                if (
                    item["id"].strip().lower() == ident_clean
                    or item["request_text"].strip().lower() == ident_clean
                ):
                    return cast(list[dict[str, Any]], item["sse_events"])
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    return None
