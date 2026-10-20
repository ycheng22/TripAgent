from typing import Literal

from pydantic import BaseModel

from core.models import BookingResult


class BookTransitArgs(BaseModel):
    itinerary_id: str
    step_index: int
    trip_id: str
    party_size: int

class BookTransitTool:
    name: str = "book_transit"
    description: str = "Book a transit trip"
    args_model = BookTransitArgs
    access: Literal["write"] = "write"
    _has_idempotency_key = True

    def execute(self, args: BookTransitArgs) -> BookingResult:
        return BookingResult(success=True, booking_reference=f"TKT-{args.trip_id}")

    def idempotency_key(self, args: BaseModel) -> str:
        if not isinstance(args, BookTransitArgs):
            raise TypeError("Invalid args")
        return f"{args.itinerary_id}:{args.step_index}:{args.trip_id}"
