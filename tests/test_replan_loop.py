from core.planner.graph import create_planner_graph
from core.planner.limits import CircuitBreakers, LimitConfig
from core.models import TripRequest
from core.audit import AuditTrail
from tests.test_validators import get_fixture

def test_replan_loop():
    breakers = CircuitBreakers(LimitConfig(max_replans=2))
    graph = create_planner_graph(breakers)
    
    # We use a fixture that violates budget, so the validate node will return violations,
    # and the graph should replan until max_replans is hit, then finalise as infeasible.
    initial_state = {
        "request": TripRequest(request_text="t", constraints=[], party_size=1, budget=10.0, days=1),
        "itinerary": get_fixture("budget_breach"), # cost is 1500
        "audit_trail": AuditTrail(),
        "replan_count": 0,
        "step_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "violations": []
    }
    
    res = graph.invoke(initial_state)
    
    assert res["status"] == "infeasible"
    assert res["plan_result"].status == "infeasible"
    assert res["replan_count"] == 2
    assert len(res["plan_result"].violations) > 0
