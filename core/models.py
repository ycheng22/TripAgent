from typing import Any, Literal
from pydantic import BaseModel, Field
import datetime

class Coordinate(BaseModel):
    lat: float
    lon: float

class Constraint(BaseModel):
    kind: str
    value: Any
    source: Literal["user", "rejection", "derived"]
    hard: bool

class TripRequest(BaseModel):
    request_text: str
    constraints: list[Constraint]
    party_size: int
    budget: float
    days: int

class Venue(BaseModel):
    venue_id: str
    name: str
    city: str
    coord: Coordinate
    source_id: str
    source_version: str

class TransitLeg(BaseModel):
    trip_id: str
    from_stop: str
    to_stop: str
    depart_at: datetime.datetime
    arrive_at: datetime.datetime
    feed_version: str
    mode: str

class ItineraryStep(BaseModel):
    step_index: int
    day: int
    kind: Literal["visit", "transit", "meal", "stay"]
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    venue: Venue | None = None
    leg: TransitLeg | None = None
    cost: float | None = None
    source_id: str
    source_version: str

class Itinerary(BaseModel):
    itinerary_id: str
    steps: list[ItineraryStep]
    total_cost: float
    currency: str

class Violation(BaseModel):
    validator: str
    severity: Literal["hard", "soft"]
    step_index: int | None
    explanation: str
    breached_constraint: str

class PendingAction(BaseModel):
    action_id: str
    tool_name: str
    args: dict[str, Any]
    idempotency_key: str
    status: Literal["pending", "approved", "rejected"]
    result: Any | None = None

class AuditRecord(BaseModel):
    step_index: int
    action_type: str
    tool_name: str | None = None
    source_id: str | None = None
    source_version: str | None = None
    duration_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    validator_failures: int
    timestamp: datetime.datetime

class PlanResult(BaseModel):
    status: Literal["finalised", "infeasible", "aborted"]
    itinerary: Itinerary | None = None
    violations: list[Violation] = Field(default_factory=list)
    which_limit: str | None = None
    audit_trail: list[AuditRecord] = Field(default_factory=list)

class OpeningHours(BaseModel):
    venue_id: str
    # simplified representation, normally would map weekday to open/close times
    open_time: datetime.time | None = None
    close_time: datetime.time | None = None
    closure_days: list[int] = Field(default_factory=list) # 0=Monday, 6=Sunday

class Price(BaseModel):
    item_id: str
    category: str
    amount: float
    currency: str

class HoldResult(BaseModel):
    success: bool
    confirmation_code: str | None = None

class BookingResult(BaseModel):
    success: bool
    booking_reference: str | None = None

class SendResult(BaseModel):
    success: bool
    delivery_status: str
