from typing import Any, TypedDict

from retrieval_core.models import ScoredHit  # type: ignore[import-untyped]

from core.audit import AuditTrail
from core.models import (
    Constraint,
    Itinerary,
    PendingAction,
    PlanResult,
    TripRequest,
    Violation,
)


class PlannerState(TypedDict):
    request: TripRequest | None
    constraints: list[Constraint]
    retrieved_hits: list[ScoredHit]
    itinerary: Itinerary | None
    violations: list[Violation]
    audit_trail: AuditTrail
    step_count: int
    total_tokens: int
    total_cost: float
    replan_count: int
    status: str
    which_limit: str | None
    plan_result: PlanResult | None
    pending_actions: list[PendingAction]
    sse_events: list[dict[str, Any]]
    grounded_context: str | None

