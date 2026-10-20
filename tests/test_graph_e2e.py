import datetime

from core.audit import AuditRecord, AuditTrail
from core.models import TripRequest
from core.planner.graph import create_planner_graph
from core.planner.limits import CircuitBreakers, LimitConfig


def test_graph_runs_end_to_end():
    breakers = CircuitBreakers(LimitConfig())
    graph = create_planner_graph(breakers)
    
    initial_state = {
        "request": TripRequest(
            request_text="test",
            constraints=[],
            party_size=2,
            budget=1000,
            days=3
        ),
        "constraints": [],
        "retrieved_hits": [],
        "itinerary": None,
        "violations": [],
        "audit_trail": AuditTrail(),
        "step_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "replan_count": 0
    }
    
    # We add a fake audit record to ensure columns exist
    initial_state["audit_trail"].append(AuditRecord(
        step_index=1,
        action_type="tool",
        tool_name="search",
        source_id="wiki",
        source_version="1.0",
        duration_ms=10,
        tokens_in=5,
        tokens_out=5,
        cost_usd=0.001,
        validator_failures=0,
        timestamp=datetime.datetime.now()
    ))
    
    res = graph.invoke(initial_state)
    
    assert res["status"] == "finalised"
    assert res["plan_result"].status == "finalised"
    
    # Check that audit trail columns are accessible
    trail = res["plan_result"].audit_trail
    assert len(trail) > 0
    assert trail[0].source_version == "1.0"

def test_graph_aborts_on_max_steps():
    # Set limit to 0 so it aborts immediately after first transition
    breakers = CircuitBreakers(LimitConfig(max_steps=0))
    graph = create_planner_graph(breakers)
    
    initial_state = {
        "step_count": 1,  # Already over limit of 0
        "audit_trail": AuditTrail(),
    }
    
    res = graph.invoke(initial_state)
    assert res["status"] == "aborted"
    assert res["plan_result"].status == "aborted"
    assert res["plan_result"].which_limit == "max_steps"
