import asyncio
import json
from pathlib import Path
from typing import Any

import asyncpg

from app.settings import settings
from core.db import init_db, save_presets

TITLES = {
    "scenario_ai_01": ("Romantic Weekend in Paris", "Romantic / Couples"),
    "scenario_ai_02": ("Amsterdam to Berlin Budget Challenge", "Transit / Budget"),
    "scenario_ai_03": ("Prague Family Heritage Holiday", "Family / Culture"),
    "scenario_ai_04": ("Paris to Vienna Grand Expedition", "Multi-City Rail"),
    "scenario_ai_05": ("Vienna Day Trip from Prague", "Day Trip"),
    "scenario_ai_06": ("Ultra Low-Cost Amsterdam", "Budget Challenge"),
    "scenario_ai_07": ("Luxury Paris Weekend", "Luxury / Romance"),
    "scenario_ai_08": ("Berlin Tram-Only Exploration", "Transit Constraints"),
    "scenario_ai_09": ("Louvre Museum Tuesday Dilemma", "Closed-Day Validator"),
    "scenario_ai_10": ("Amsterdam-Berlin-Prague Marathon", "Multi-City Transit"),
    "scenario_ai_11": ("Vienna Museum Blitz", "Schedule Limits"),
    "scenario_ai_12": ("Prague Friends Getaway", "Friends / Group"),
    "scenario_ai_13": ("Paris to Amsterdam Express Train", "Inter-City Rail"),
    "scenario_ai_14": ("Berlin to Amsterdam Art Excursion", "Culture / Museum"),
    "scenario_ai_15": ("Vienna Week of Splendor", "Extended Stay"),
    "scenario_ai_16": ("Amsterdam Transit-Heavy Weekend", "Mobility Preference"),
    "scenario_ai_17": ("Five European Capitals in 2 Days", "Feasibility Boundary"),
    "scenario_ai_18": ("Student Budget Prague Adventure", "Student Budget"),
    "scenario_ai_19": ("Paris Art Lover's Immersion", "Art & Culture"),
    "scenario_ai_20": ("Vienna to Paris Nightjet Sleeper", "Human-in-the-Loop"),
}


async def main() -> None:
    eval_file = Path("eval_runs/run_deepseek_6babf91_20261020T023119Z.jsonl")
    if not eval_file.exists():
        print(f"Error: Eval file not found at {eval_file}")
        return

    lines = eval_file.read_text(encoding="utf-8").splitlines()
    run_data = json.loads(lines[0])

    results = run_data["results"]
    print(f"Found {len(results)} evaluated scenario runs.")

    presets: list[dict[str, Any]] = []
    demo_cache: dict[str, Any] = {}

    for i in range(1, 21):
        sc_id = f"scenario_ai_{i:02d}"
        sc_file = Path(f"evals/scenarios/{sc_id}.json")
        sc_json = json.loads(sc_file.read_text(encoding="utf-8")) if sc_file.exists() else {}

        # Corresponding evaluated run result
        r = results[i - 1]
        state = r["state"]
        events = state.get("sse_events", [])
        plan_result = state.get("plan_result")
        itinerary = state.get("itinerary") or (plan_result.get("itinerary") if plan_result else None)

        total_cost = 0.0
        steps = []
        if itinerary:
            total_cost = float(itinerary.get("total_cost", 0.0))
            steps = itinerary.get("steps", [])

        title, category = TITLES.get(sc_id, (f"Preset Scenario {i}", "General"))
        req_text = sc_json.get("request_text") or r["scenario"]["request_text"]
        constraints = sc_json.get("constraints", {})

        preset_data = {
            "id": sc_id,
            "title": title,
            "category": category,
            "request_text": req_text,
            "days": constraints.get("days", 1),
            "budget_eur": float(constraints.get("budget_eur", 0.0)),
            "party_size": constraints.get("party_size", 1),
            "expected_feasibility": sc_json.get("expected_feasibility", "feasible"),
            "total_cost": total_cost,
            "step_count": len(steps),
            "sse_events": events,
            "plan_result": plan_result,
        }
        presets.append(preset_data)

        # Index in demo_cache for fast instant lookup by text or id
        demo_cache[req_text.strip().lower()] = events
        demo_cache[sc_id.lower()] = events

    # Save to data/preset_cache.json
    preset_cache_file = Path("data/preset_cache.json")
    preset_cache_file.write_text(json.dumps(presets, indent=2), encoding="utf-8")
    print(f"Saved {len(presets)} presets to {preset_cache_file}")

    # Also update data/demo_cache.json with all 20 scenarios
    demo_cache_file = Path("data/demo_cache.json")
    demo_cache_file.write_text(json.dumps(demo_cache, indent=2), encoding="utf-8")
    print(f"Updated {demo_cache_file} with {len(demo_cache)} scenario mappings.")

    # Save to Neon Database if DATABASE_URL is available
    db_url = settings.database_url
    if db_url:
        print(f"Connecting to Neon database: {db_url[:40]}...")
        try:
            await init_db(db_url)
            print("Initialized Neon table preset_scenarios.")
            await save_presets(db_url, presets)
            print(f"Successfully saved all {len(presets)} presets to Neon PostgreSQL database!")
        except (OSError, asyncpg.PostgresError) as e:
            print(f"Error seeding Neon database: {type(e)} {e}")
    else:
        print("DATABASE_URL not set in settings, skipped Neon seeding.")


if __name__ == "__main__":
    asyncio.run(main())
