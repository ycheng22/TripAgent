from typing import Literal

from pydantic import BaseModel

from core.models import HoldResult


class HoldReservationArgs(BaseModel):
    itinerary_id: str
    step_index: int
    resource_id: str
    party_size: int

class HoldReservationTool:
    name: str = "hold_reservation"
    description: str = "Hold a reservation for a resource"
    args_model = HoldReservationArgs
    access: Literal["write"] = "write"
    _has_idempotency_key = True

    def execute(self, args: HoldReservationArgs) -> HoldResult:
        return HoldResult(success=True, confirmation_code=f"HOLD-{args.resource_id}")

    def idempotency_key(self, args: BaseModel) -> str:
        if not isinstance(args, HoldReservationArgs):
            raise TypeError("Invalid args")
        return f"{args.itinerary_id}:{args.step_index}:{args.resource_id}"
