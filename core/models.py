import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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

    @property
    def cost(self) -> float:
        return self.cost_usd

import json
from pathlib import Path


class AuditTrail(BaseModel):
    records: list[AuditRecord] = Field(default_factory=list)
    
    def append(self, record: AuditRecord) -> None:
        self.records.append(record)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> AuditRecord:
        return self.records[idx]

    def __iter__(self) -> Any:
        return iter(self.records)

    def to_markdown(self) -> str:
        if not self.records:
            return "No audit records."
        
        headers = [
            "step_index", "action_type", "tool_name", "source_id", "source_version", 
            "duration_ms", "tokens_in", "tokens_out", "cost_usd", "validator_failures", "timestamp"
        ]
        
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        
        for r in self.records:
            row = [
                str(r.step_index),
                r.action_type,
                str(r.tool_name or ""),
                str(r.source_id or ""),
                str(r.source_version or ""),
                str(r.duration_ms),
                str(r.tokens_in),
                str(r.tokens_out),
                f"{r.cost_usd:.4f}",
                str(r.validator_failures),
                r.timestamp.isoformat()
            ]
            lines.append("| " + " | ".join(row) + " |")
            
        return "\n".join(lines)

    def to_json(self, run_id: str, base_dir: Path) -> Path:
        base_dir.mkdir(parents=True, exist_ok=True)
        out_path = base_dir / f"{run_id}.json"
        data = [json.loads(r.model_dump_json()) for r in self.records]
        out_path.write_text(json.dumps(data, indent=2))
        return out_path

class PlanResult(BaseModel):
    status: Literal["finalised", "infeasible", "aborted"]
    itinerary: Itinerary | None = None
    violations: list[Violation] = Field(default_factory=list)
    which_limit: str | None = None
    audit_trail: AuditTrail = Field(default_factory=AuditTrail)

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
