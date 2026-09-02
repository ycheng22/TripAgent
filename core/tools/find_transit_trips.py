from pydantic import BaseModel
from typing import Literal
import datetime
from core.models import TransitLeg

class FindTransitTripsArgs(BaseModel):
    from_stop: str
    to_stop: str
    depart_after: datetime.datetime

class FindTransitTripsTool:
    name: str = "find_transit_trips"
    description: str = "Find transit trips between two stops"
    args_model = FindTransitTripsArgs
    access: Literal["read"] = "read"

    def execute(self, args: FindTransitTripsArgs) -> list[TransitLeg]:
        # Stub implementation
        return [
            TransitLeg(
                trip_id="stub-trip-1",
                from_stop=args.from_stop,
                to_stop=args.to_stop,
                depart_at=args.depart_after + datetime.timedelta(minutes=15),
                arrive_at=args.depart_after + datetime.timedelta(minutes=45),
                feed_version="2024-01-stub",
                mode="train"
            )
        ]
