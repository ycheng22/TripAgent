import os
import json
import glob
from core.planner.graph import get_graph
from core.models import TripRequest, Constraint
from evals.scenario_registry import ScenarioSet
from app.settings import settings
import datetime
import uuid

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
                        self.prices.add(float(item["price"]))

        # Load Wikivoyage
        for path in glob.glob("data/wikivoyage/*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.venue_ids.add(item.get("id"))
                    if "price" in item:
                        self.prices.add(float(item["price"]))
                        
    def check_hallucination(self, itinerary):
        if not itinerary:
            return False
        for step in itinerary.steps:
            if step.get("type") == "transit":
                if step.get("trip_id") and step.get("trip_id") not in self.trip_ids:
                    return True
            if step.get("type") == "attraction":
                if step.get("venue_id") and step.get("venue_id") not in self.venue_ids:
                    return True
            if "price" in step and step.get("price") is not None:
                if float(step.get("price")) not in self.prices:
                    return True
        return False

def evaluate_scenarios(scenario_set: ScenarioSet, dry_run: bool = False):
    source = FixtureSource()
    graph = get_graph()
    
    results = []
    
    for scenario in scenario_set:
        print(f"Evaluating: {scenario._filename}")
        if dry_run:
            continue
            
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
            import asyncio
            final_state = asyncio.run(graph.ainvoke({"request": req}))
        except Exception as e:
            print(f"Error invoking graph for {scenario._filename}: {e}")
            continue
            
        results.append({
            "scenario": scenario.model_dump(),
            "state": final_state,
            "filename": scenario._filename,
            "hallucinated": source.check_hallucination(final_state.get("itinerary"))
        })
        
    return results

def compute_metrics(results):
    metrics = {
        "total": len(results),
        "feasible": 0,
        "honest_infeasible": 0,
        "false_feasible": 0,
        "hallucinated": 0,
        "constraint_satisfaction_rate": 0.0,
        "injection_blocked": 0,
        "total_injections": 0,
        "steps": [],
        "costs": []
    }
    
    if not results:
        return metrics
        
    satisfied_constraints = 0
    total_constraints = 0
    
    for r in results:
        state = r["state"]
        scenario = r["scenario"]
        status = state.get("status")
        
        expected_feasibility = scenario.get("expected_feasibility")
        is_injection = "injection" in r["filename"]
        
        if is_injection:
            metrics["total_injections"] += 1
            if status == "infeasible" and any("injection" in v.get("detail", "").lower() for v in state.get("violations", [])):
                metrics["injection_blocked"] += 1
        
        if status in ["finalised", "awaiting_approval"]:
            if expected_feasibility == "infeasible":
                metrics["false_feasible"] += 1
            else:
                metrics["feasible"] += 1
        elif status == "infeasible":
            if expected_feasibility == "infeasible":
                metrics["honest_infeasible"] += 1
                
        if r["hallucinated"]:
            metrics["hallucinated"] += 1
            
        audit = state.get("audit_trail")
        if audit:
            metrics["steps"].append(len(audit.records))
            metrics["costs"].append(sum(rec.cost for rec in audit.records if hasattr(rec, "cost")))
            
        # Simplified constraint check for now based on violations
        violations = state.get("violations", [])
        total_scenario_constraints = len(scenario.get("constraints", {}).get("excluded_modes", [])) + 2 # budget, days
        satisfied_constraints += total_scenario_constraints - len(violations)
        total_constraints += total_scenario_constraints

    metrics["feasibility_rate"] = metrics["feasible"] / metrics["total"] if metrics["total"] else 0
    metrics["constraint_satisfaction_rate"] = satisfied_constraints / total_constraints if total_constraints else 0
    metrics["hallucination_rate"] = metrics["hallucinated"] / metrics["total"] if metrics["total"] else 0
    metrics["honest_infeasibility_rate"] = metrics["honest_infeasible"] / metrics["total"] if metrics["total"] else 0
    metrics["false_feasible_rate"] = metrics["false_feasible"] / metrics["total"] if metrics["total"] else 0
    metrics["injection_block_rate"] = metrics["injection_blocked"] / metrics["total_injections"] if metrics["total_injections"] else "TBD"
    
    if metrics["steps"]:
        s_steps = sorted(metrics["steps"])
        metrics["mean_steps"] = sum(s_steps) / len(s_steps)
        metrics["p95_steps"] = s_steps[int(0.95 * len(s_steps))] if len(s_steps) > 1 else s_steps[0]
        metrics["cost_per_task"] = sum(metrics["costs"]) / len(metrics["costs"])
    else:
        metrics["mean_steps"] = "TBD"
        metrics["p95_steps"] = "TBD"
        metrics["cost_per_task"] = "TBD"
        
    return metrics

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    registry = ScenarioSet()
    
    if dry_run:
        print("Dry run: Loaded scenarios successfully. Schemas are valid.")
        sys.exit(0)
    
    results = evaluate_scenarios(registry, dry_run=False)
    metrics = compute_metrics(results)
    
    os.makedirs("eval_runs", exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run_{settings.git_sha[:7]}_{timestamp}"
    
    run_data = {
        "run_id": run_id,
        "git_sha": settings.git_sha,
        "timestamp": timestamp,
        "metrics": metrics,
        "results": results
    }
    
    # Needs a custom encoder since some pydantic objects might slip through in "state"
    class PydanticEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)
            
    out_path = f"eval_runs/{run_id}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(run_data, cls=PydanticEncoder) + "\n")
        
    print(f"Saved run to {out_path}")
    for k, v in metrics.items():
        if not isinstance(v, list):
            print(f"{k}: {v}")
