import asyncio
import datetime
import json
import os
import re
from pathlib import Path

from core.models import TripRequest
from core.planner.graph import get_graph


async def precompute():
    content = Path("docs/DEMO-SCENARIOS.md").read_text(encoding="utf-8")

    scenarios = re.findall(r"\*\*Scenario\*\*: `(.*?)`", content)
    print(f"Found {len(scenarios)} demo scenarios.")

    graph = get_graph()
    cache = {}

    for i, request_text in enumerate(scenarios):
        print(f"Precomputing [{i+1}/{len(scenarios)}]: {request_text}")

        # Extract days
        days_match = re.search(r"(\d+)\s*days?", request_text, re.IGNORECASE)
        days = int(days_match.group(1)) if days_match else 2

        # Extract budget
        budget_match = re.search(
            r"(\d+)\s*(?:EUR|€)|(?:EUR|€)\s*(\d+)|budget\s+(?:is\s+)?(?:EUR\s+)?(\d+)",
            request_text,
            re.IGNORECASE,
        )
        if budget_match:
            budget = float(budget_match.group(1) or budget_match.group(2) or budget_match.group(3))
        else:
            budget = 1000.0

        req = TripRequest(
            request_text=request_text,
            constraints=[],
            party_size=2 if "couple" in request_text.lower() or "weekend" in request_text.lower() else 1,
            budget=budget,
            days=days,
        )

        events = []
        seen_count = 0

        try:
            async for step in graph.astream({"request": req}, stream_mode="values"):
                step_events = step.get("sse_events", [])
                while seen_count < len(step_events):
                    ev = step_events[seen_count]
                    events.append(ev)
                    seen_count += 1
        except Exception as e:  # noqa: BLE001
            events.append({"event_type": "error", "payload": {"detail": str(e)}})

        cache[request_text.strip().lower()] = events

    os.makedirs("data", exist_ok=True)

    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)

    Path("data/demo_cache.json").write_text(json.dumps(cache, indent=2, cls=CustomEncoder), encoding="utf-8")
    print("Precomputation complete. Saved to data/demo_cache.json")


if __name__ == "__main__":
    asyncio.run(precompute())
