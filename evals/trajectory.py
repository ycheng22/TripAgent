import argparse
import datetime
import glob
import json
import os
from typing import Any, Literal

from app.settings import settings
from core.models import Constraint, TripRequest
from core.planner.graph import get_graph
from evals.scenario_registry import ScenarioSet
from providers.factory import create_provider


class FixtureSource:
    def __init__(self) -> None:
        self.trip_ids: set[str] = set()
        self.venue_ids: set[str] = set()
        self.prices: set[float] = {0.0}
        self._load()

    def _load(self) -> None:
        # Load GTFS
        for path in glob.glob("data/gtfs/*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if item.get("trip_id"):
                        self.trip_ids.add(item["trip_id"])
                    if "price" in item:
                        self.prices.add(float(item["price"]))

        # Load Wikivoyage
        for path in glob.glob("data/wikivoyage/*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    vid = item.get("venue_id") or item.get("id")
                    if vid:
                        self.venue_ids.add(vid)
                    if "prices" in item and isinstance(item["prices"], list):
                        for p in item["prices"]:
                            if "amount" in p:
                                self.prices.add(float(p["amount"]))
                    elif "price" in item:
                        self.prices.add(float(item["price"]))

    def check_hallucination(self, itinerary: Any) -> bool:
        if not itinerary:
            return False
        steps = getattr(itinerary, "steps", None)
        if steps is None and isinstance(itinerary, dict):
            steps = itinerary.get("steps", [])
        if not steps:
            return False

        for step in steps:
            step_type = getattr(step, "kind", None) or (
                step.get("kind") or step.get("type") if isinstance(step, dict) else None
            )
            if step_type == "transit":
                leg = getattr(step, "leg", None)
                trip_id = leg.trip_id if leg else (
                    step.get("trip_id") or (step.get("leg") or {}).get("trip_id")
                    if isinstance(step, dict)
                    else None
                )
                if trip_id and trip_id not in self.trip_ids:
                    return True

            if step_type in ("visit", "attraction"):
                venue = getattr(step, "venue", None)
                venue_id = venue.venue_id if venue else (
                    step.get("venue_id") or (step.get("venue_id") or (step.get("venue") or {}).get("venue_id"))
                    if isinstance(step, dict)
                    else None
                )
                if venue_id and venue_id not in self.venue_ids:
                    return True

            cost = getattr(step, "cost", None) or (
                step.get("cost") or step.get("price") if isinstance(step, dict) else None
            )
            if cost is not None and float(cost) not in self.prices:
                return True

        return False


def evaluate_scenarios(
    scenario_set: ScenarioSet,
    provider_name: str = "deepseek",
    dry_run: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    source = FixtureSource()
    tier: Literal["low_cost", "western_hosted"] = "low_cost" if provider_name == "deepseek" else "western_hosted"
    provider = create_provider(tier, settings=settings)
    graph = get_graph(provider=provider)

    results = []
    scenarios_to_run = list(scenario_set)
    if limit is not None:
        scenarios_to_run = scenarios_to_run[:limit]

    for scenario in scenarios_to_run:
        print(f"Evaluating: {scenario._filename} with {provider.provider_name} ({provider.model})", flush=True)
        if dry_run:
            continue

        req_constraints = []
        for mode in scenario.constraints.excluded_modes:
            req_constraints.append(
                Constraint(kind="exclude_mode", value=mode, source="user", hard=True)
            )

        req = TripRequest(
            request_text=scenario.request_text,
            constraints=req_constraints,
            party_size=scenario.constraints.party_size or 1,
            budget=scenario.constraints.budget_eur or 0.0,
            days=scenario.constraints.days or 1,
        )

        try:
            import asyncio
            final_state = asyncio.run(graph.ainvoke({"request": req}))
        except (ValueError, RuntimeError, OSError, TimeoutError) as e:
            print(f"Error invoking graph for {scenario._filename}: {e}", flush=True)
            continue

        itin = final_state.get("itinerary")
        is_hallucinated = source.check_hallucination(itin)

        results.append({
            "scenario": scenario.model_dump(),
            "state": final_state,
            "filename": scenario._filename,
            "hallucinated": is_hallucinated,
        })

    return results


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "total": len(results),
        "feasible": 0,
        "honest_infeasible": 0,
        "false_feasible": 0,
        "hallucinated": 0,
        "constraint_satisfaction_rate": 0.0,
        "injection_blocked": 0,
        "total_injections": 0,
        "steps": [],
        "costs": [],
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
        elif status == "infeasible" and expected_feasibility == "infeasible":
            metrics["honest_infeasible"] += 1

        if r["hallucinated"]:
            metrics["hallucinated"] += 1

        audit = state.get("audit_trail")
        if audit:
            records = getattr(audit, "records", audit if isinstance(audit, list) else [])
            metrics["steps"].append(len(records))
            metrics["costs"].append(sum(rec.cost for rec in records if hasattr(rec, "cost")))

        # Constraint satisfaction
        violations = state.get("violations", [])
        total_scenario_constraints = len(scenario.get("constraints", {}).get("excluded_modes", [])) + 2
        satisfied_constraints += max(0, total_scenario_constraints - len(violations))
        total_constraints += total_scenario_constraints

    metrics["feasibility_rate"] = metrics["feasible"] / metrics["total"] if metrics["total"] else 0
    metrics["constraint_satisfaction_rate"] = (
        satisfied_constraints / total_constraints if total_constraints else 0
    )
    metrics["hallucination_rate"] = metrics["hallucinated"] / metrics["total"] if metrics["total"] else 0
    metrics["honest_infeasibility_rate"] = (
        metrics["honest_infeasible"] / metrics["total"] if metrics["total"] else 0
    )
    metrics["false_feasible_rate"] = metrics["false_feasible"] / metrics["total"] if metrics["total"] else 0
    metrics["injection_block_rate"] = (
        metrics["injection_blocked"] / metrics["total_injections"]
        if metrics["total_injections"]
        else "N/A"
    )

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
    parser = argparse.ArgumentParser(description="Run trajectory evals on TripAgent.")
    parser.add_argument("--provider", choices=["deepseek", "openai"], default=settings.default_eval_provider)
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios to evaluate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry = ScenarioSet()

    if args.dry_run:
        print("Dry run: Loaded scenarios successfully. Schemas are valid.")
        import sys
        sys.exit(0)

    results = evaluate_scenarios(registry, provider_name=args.provider, dry_run=False, limit=args.limit)
    metrics = compute_metrics(results)

    os.makedirs("eval_runs", exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run_{args.provider}_{settings.git_sha[:7]}_{timestamp}"

    run_data = {
        "run_id": run_id,
        "provider": args.provider,
        "git_sha": settings.git_sha,
        "timestamp": timestamp,
        "metrics": metrics,
        "results": results,
    }

    class PydanticEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)

    out_path = f"eval_runs/{run_id}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(run_data, cls=PydanticEncoder) + "\n")

    print(f"\n=== Evaluation Finished for {args.provider} ===")
    print(f"Saved run to {out_path}")
    for k, v in metrics.items():
        if not isinstance(v, list):
            print(f"  {k}: {v}")
