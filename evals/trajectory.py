import os
import json
import glob
from core.planner.graph import get_graph
from core.models import TripRequest, Constraint
from evals.scenario_registry import ScenarioSet
from app.settings import settings
import datetime

class FixtureSource:
    def __init__(self):
        self.trip_ids = set()
        self.venue_ids = set()
        self.prices = set()
        self._load()

    def _load(self):
        # Load GTFS
        for path in glob.glob("data/gtfs/*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.trip_ids.add(item.get("trip_id"))
                    if "price" in item:
                        self.prices.add(item["price"])

        # Load Wikivoyage
        for path in glob.glob("data/wikivoyage/*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.venue_ids.add(item.get("id"))
                    if "price" in item:
                        self.prices.add(item["price"])

def evaluate_scenarios(scenario_set: ScenarioSet, dry_run: bool = False):
    source = FixtureSource()
    graph = get_graph()
    
    results = []
    
    for scenario in scenario_set:
        print(f"Evaluating: {scenario._filename}")
        if dry_run:
            continue
            
        # Convert to TripRequest
        req_constraints = []
        for mode in scenario.constraints.excluded_modes:
            req_constraints.append(Constraint(
                kind="exclude_mode", value=mode, source="user", hard=True
            ))
            
        req = TripRequest(
            request_text=scenario.request_text,
            constraints=req_constraints,
            party_size=scenario.constraints.party_size or 1,
            budget=scenario.constraints.budget_eur or 0.0,
            days=scenario.constraints.days or 1
        )
        
        try:
            # We use ainvoke as the graph is async
            import asyncio
            # In an actual script, we would use asyncio.run if this is the main entry point,
            # but since we might be in a loop, let's just get the event loop
            final_state = asyncio.run(graph.ainvoke({"request": req}))
        except Exception as e:
            print(f"Error invoking graph for {scenario._filename}: {e}")
            continue
            
        results.append({
            "scenario": scenario,
            "state": final_state
        })
        
    return results, source

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    registry = ScenarioSet()
    
    if dry_run:
        print("Dry run: Loaded scenarios successfully. Schemas are valid.")
        sys.exit(0)
    
    print("Run evaluators here...")
    
