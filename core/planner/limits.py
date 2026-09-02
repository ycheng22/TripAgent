from pydantic import BaseModel
from typing import Any
from core.models import Violation, Itinerary
from core.audit import AuditTrail

class LimitConfig(BaseModel):
    max_steps: int = 25
    max_tokens_per_task: int = 60000
    max_cost_per_task: float = 0.05
    max_replans: int = 3

class LimitBreached(Exception):
    def __init__(self, which_limit: str, itinerary: Itinerary | None, audit_trail: AuditTrail) -> None:
        self.which_limit = which_limit
        self.itinerary = itinerary
        self.audit_trail = audit_trail
        super().__init__(f"Limit breached: {which_limit}")

class CircuitBreakers:
    def __init__(self, config: LimitConfig) -> None:
        self.config = config

    def check(self, step_count: int, total_tokens: int, total_cost: float) -> str | None:
        """Returns the limit name if breached, else None"""
        if step_count > self.config.max_steps:
            return "max_steps"
        if total_tokens > self.config.max_tokens_per_task:
            return "max_tokens"
        if total_cost > self.config.max_cost_per_task:
            return "max_cost"
        return None
