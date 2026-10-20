from collections.abc import Callable
from typing import Any

from core.models import AuditTrail, PlanResult
from core.planner.limits import CircuitBreakers
from core.planner.state import PlannerState


def create_abort_node(breakers: CircuitBreakers) -> Callable[[PlannerState], dict[str, Any]]:
    def abort_node(state: PlannerState) -> dict[str, Any]:
        limit = breakers.check(
            state.get("step_count", 0),
            state.get("total_tokens", 0),
            state.get("total_cost", 0.0)
        )
        result = PlanResult(
            status="aborted",
            itinerary=state.get("itinerary"),
            violations=state.get("violations", []),
            which_limit=limit or "unknown",
            audit_trail=state.get("audit_trail") if state.get("audit_trail") else AuditTrail()
        )
        return {"plan_result": result, "status": "aborted", "which_limit": limit}
    return abort_node
