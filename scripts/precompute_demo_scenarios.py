import asyncio
import json
import os
import re
from core.planner.graph import get_graph
from core.models import TripRequest

async def precompute():
    with open("docs/DEMO-SCENARIOS.md", "r", encoding="utf-8") as f:
        content = f.read()
        
    scenarios = re.findall(r"\*\*Scenario\*\*: `(.*?)`", content)
    print(f"Found {len(scenarios)} demo scenarios.")
    
    graph = get_graph()
    cache = {}
    
    for i, request_text in enumerate(scenarios):
        print(f"Precomputing [{i+1}/{len(scenarios)}]: {request_text}")
        req = TripRequest(
            request_text=request_text,
            constraints=[],
            party_size=1,
            budget=0.0,
            days=1
        )
        
        events = []
        seen_count = 0
        
        try:
            async for step in graph.astream({"user_input": req}, stream_mode="values"):
                step_events = step.get("sse_events", [])
                while seen_count < len(step_events):
                    ev = step_events[seen_count]
                    events.append(ev)
                    seen_count += 1
        except Exception as e:
            events.append({"event_type": "error", "payload": {"detail": str(e)}})
            
        cache[request_text.strip().lower()] = events
        
    os.makedirs("data", exist_ok=True)
    
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            import datetime
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)
            
    with open("data/demo_cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, cls=CustomEncoder)
        
    print("Precomputation complete. Saved to data/demo_cache.json")

if __name__ == "__main__":
    asyncio.run(precompute())
