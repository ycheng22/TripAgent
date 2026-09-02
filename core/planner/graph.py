from langgraph.graph import StateGraph, END
from typing import Any
from core.planner.state import PlannerState
from core.planner.abort import create_abort_node
from core.models import Constraint, Itinerary, PlanResult, AuditRecord
from core.planner.limits import CircuitBreakers, LimitConfig
from retrieval_core.models import ScoredHit

def parse_constraints(state: PlannerState) -> dict[str, Any]:
    # Stub: Return fixed constraints
    return {"constraints": []}

def retrieve(state: PlannerState) -> dict[str, Any]:
    # Stub: Return empty hits for now
    return {"retrieved_hits": []}

def draft_itinerary(state: PlannerState) -> dict[str, Any]:
    if state.get("itinerary"):
        return {"itinerary": state["itinerary"]}
        
    # Stub: Build a fixed empty itinerary
    itin = Itinerary(
        itinerary_id="stub-itin",
        steps=[],
        total_cost=0.0,
        currency="EUR"
    )
    return {"itinerary": itin}

from core.validators.budget import BudgetValidator
from core.validators.opening_hours import OpeningHoursValidator
from core.validators.geography import GeographyValidator
from core.validators.connectivity import ConnectivityValidator

def validate(state: PlannerState) -> dict[str, Any]:
    itin = state.get("itinerary")
    req = state.get("request")
    if not itin or not req:
        return {"violations": []}
        
    validators = [
        BudgetValidator(),
        OpeningHoursValidator(),
        GeographyValidator(),
        ConnectivityValidator()
    ]
    
    violations = []
    for v in validators:
        violations.extend(v.validate(itin, req))
        
    return {"violations": violations}

def replan(state: PlannerState) -> dict[str, Any]:
    count = state.get("replan_count", 0) + 1
    return {"replan_count": count}

def finalise(state: PlannerState) -> dict[str, Any]:
    status = "finalised"
    if state.get("violations"):
        status = "infeasible"
    
    result = PlanResult(
        status=status,
        itinerary=state.get("itinerary"),
        violations=state.get("violations", []),
        audit_trail=state.get("audit_trail").records if state.get("audit_trail") else []
    )
    return {"plan_result": result, "status": status}

def create_planner_graph(breakers: CircuitBreakers) -> StateGraph:
    builder = StateGraph(PlannerState)
    
    builder.add_node("parse_constraints", parse_constraints)
    builder.add_node("retrieve", retrieve)
    builder.add_node("draft_itinerary", draft_itinerary)
    builder.add_node("validate", validate)
    builder.add_node("replan", replan)
    builder.add_node("finalise", finalise)
    builder.add_node("abort", create_abort_node(breakers))
    
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
        return "finalise"

    builder.add_conditional_edges("validate", after_validate)
    
    builder.add_conditional_edges("replan", check_limits_or_next("draft_itinerary"))
    
    builder.add_edge("finalise", END)
    builder.add_edge("abort", END)
    
    return builder.compile()
