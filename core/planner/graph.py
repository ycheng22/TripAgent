from langgraph.graph import StateGraph, END
from typing import Any
from core.planner.state import PlannerState
from core.planner.abort import create_abort_node
from core.models import Constraint, Itinerary, PlanResult, AuditRecord
from core.planner.limits import CircuitBreakers, LimitConfig
from retrieval_core.models import ScoredHit
from core.planner.events import emit_event
from core.validators.budget import BudgetValidator
from core.validators.opening_hours import OpeningHoursValidator
from core.validators.geography import GeographyValidator
from core.validators.connectivity import ConnectivityValidator
from core.approval import get_approval_queue

def parse_constraints(state: PlannerState) -> dict[str, Any]:
    # Stub: Return fixed constraints
    ev = emit_event("constraints_parsed", {"constraints": []})
    events = state.get("sse_events", []) + [ev.model_dump()]
    return {"constraints": [], "sse_events": events}

def retrieve(state: PlannerState) -> dict[str, Any]:
    # Stub: Return empty hits for now
    ev = emit_event("retrieving", {"hits_count": 0})
    events = state.get("sse_events", []) + [ev.model_dump()]
    return {"retrieved_hits": [], "sse_events": events}

def draft_itinerary(state: PlannerState) -> dict[str, Any]:
    if state.get("itinerary"):
        ev = emit_event("drafting", {"itinerary": state["itinerary"].model_dump()})
        events = state.get("sse_events", []) + [ev.model_dump()]
        return {"itinerary": state["itinerary"], "sse_events": events}
        
    # Stub: Build a fixed empty itinerary
    itin = Itinerary(
        itinerary_id="stub-itin",
        steps=[],
        total_cost=0.0,
        currency="EUR"
    )
    ev = emit_event("drafting", {"itinerary": itin.model_dump()})
    events = state.get("sse_events", []) + [ev.model_dump()]
    return {"itinerary": itin, "sse_events": events}

def validate(state: PlannerState) -> dict[str, Any]:
    itin = state.get("itinerary")
    req = state.get("request")
    
    events = state.get("sse_events", [])
    events.append(emit_event("validating", {}).model_dump())
    
    if not itin or not req:
        return {"violations": [], "sse_events": events}
        
    validators = [
        BudgetValidator(),
        OpeningHoursValidator(),
        GeographyValidator(),
        ConnectivityValidator()
    ]
    
    violations = []
    for v in validators:
        violations.extend(v.validate(itin, req))
        
    if violations:
        events.append(emit_event("violation_found", {"violations": [v.model_dump() for v in violations]}).model_dump())
        
    return {"violations": violations, "sse_events": events}

def replan(state: PlannerState) -> dict[str, Any]:
    count = state.get("replan_count", 0) + 1
    ev = emit_event("replanning", {"replan_count": count})
    events = state.get("sse_events", []) + [ev.model_dump()]
    return {"replan_count": count, "sse_events": events}

async def execute_writes(state: PlannerState) -> dict[str, Any]:
    itin = state.get("itinerary")
    events = state.get("sse_events", [])
    if not itin:
        return {"pending_actions": [], "sse_events": events}
        
    queue = get_approval_queue()
    pending = []
    
    for i, step in enumerate(itin.steps):
        if step.get("type") == "transit":
            key = f"{itin.itinerary_id}-{i}-book"
            action = await queue.submit("book_transit", {"trip_id": step.get("trip_id")}, key)
            if action.status == "pending":
                pending.append(action)
            elif action.status == "rejected":
                events.append(emit_event("violation_found", {"violations": [{"rule": "approval", "detail": "User rejected booking"}]}).model_dump())
                return {"status": "infeasible", "violations": [{"rule": "approval", "detail": "User rejected booking"}], "sse_events": events}
                
    if pending:
        events.append(emit_event("awaiting_approval", {"pending_actions": [p.model_dump() for p in pending]}).model_dump())
        return {"status": "awaiting_approval", "pending_actions": pending, "sse_events": events}
    return {"pending_actions": [], "sse_events": events}

def finalise(state: PlannerState) -> dict[str, Any]:
    status = state.get("status")
    if not status or status not in ["awaiting_approval", "infeasible"]:
        status = "finalised"
        if state.get("violations"):
            status = "infeasible"
    
    result = PlanResult(
        status=status,
        itinerary=state.get("itinerary"),
        violations=state.get("violations", []),
        audit_trail=state.get("audit_trail").records if state.get("audit_trail") else []
    )
    
    events = state.get("sse_events", [])
    if status == "finalised":
        events.append(emit_event("finalised", {"plan_result": result.model_dump()}).model_dump())
    elif status == "infeasible":
        events.append(emit_event("infeasible", {"plan_result": result.model_dump()}).model_dump())
        
    return {"plan_result": result, "status": status, "sse_events": events}

def wrap_abort(breakers: CircuitBreakers):
    node = create_abort_node(breakers)
    def wrapped(state: PlannerState) -> dict[str, Any]:
        res = node(state)
        ev = emit_event("aborted", {"which_limit": res.get("which_limit")})
        events = state.get("sse_events", []) + [ev.model_dump()]
        res["sse_events"] = events
        return res
    return wrapped

def create_planner_graph(breakers: CircuitBreakers) -> StateGraph:
    builder = StateGraph(PlannerState)
    
    builder.add_node("parse_constraints", parse_constraints)
    builder.add_node("retrieve", retrieve)
    builder.add_node("draft_itinerary", draft_itinerary)
    builder.add_node("validate", validate)
    builder.add_node("replan", replan)
    builder.add_node("execute_writes", execute_writes)
    builder.add_node("finalise", finalise)
    builder.add_node("abort", wrap_abort(breakers))
    
    def check_limits_or_next(next_node: str):
        def _check(state: PlannerState) -> str:
            limit = breakers.check(
                state.get("step_count", 0),
                state.get("total_tokens", 0),
                state.get("total_cost", 0.0)
            )
            if limit:
                return "abort"
            return next_node
        return _check

    builder.set_entry_point("parse_constraints")
    
    builder.add_conditional_edges("parse_constraints", check_limits_or_next("retrieve"))
    builder.add_conditional_edges("retrieve", check_limits_or_next("draft_itinerary"))
    builder.add_conditional_edges("draft_itinerary", check_limits_or_next("validate"))
    
    def after_validate(state: PlannerState) -> str:
        limit = breakers.check(
            state.get("step_count", 0),
            state.get("total_tokens", 0),
            state.get("total_cost", 0.0)
        )
        if limit:
            return "abort"
            
        violations = state.get("violations", [])
        if violations:
            if state.get("replan_count", 0) < breakers.config.max_replans:
                return "replan"
            return "finalise"
        return "execute_writes"

    builder.add_conditional_edges("validate", after_validate)
    
    builder.add_conditional_edges("replan", check_limits_or_next("draft_itinerary"))
    
    def after_writes(state: PlannerState) -> str:
        if state.get("status") == "awaiting_approval":
            return "finalise"
        return "finalise"
        
    builder.add_conditional_edges("execute_writes", after_writes)
    
    builder.add_edge("finalise", END)
    builder.add_edge("abort", END)
    
    return builder.compile()

# Global graph for simple access
_graph = None
def get_graph() -> StateGraph:
    global _graph
    if _graph is None:
        from core.planner.limits import LimitConfig
        breakers = CircuitBreakers(LimitConfig())
        _graph = create_planner_graph(breakers)
    return _graph
