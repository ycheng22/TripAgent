from pydantic import BaseModel
from typing import Literal
import datetime
from core.models import TransitLeg
from pathlib import Path
import json

class FindTransitTripsArgs(BaseModel):
    from_stop: str
    to_stop: str
    depart_after: str # ISO datetime string

class FindTransitTripsTool:
    name: str = "find_transit_trips"
    description: str = "Find available transit trips between two stops after a certain time."
    args_model = FindTransitTripsArgs
    access: Literal["read"] = "read"

    def execute(self, args: FindTransitTripsArgs) -> list[TransitLeg]:
        depart_after_dt = datetime.datetime.fromisoformat(args.depart_after)
        target_date = depart_after_dt.date()
        
        path = Path("data/gtfs/transit_legs.json")
        legs = []
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for t in data:
                if t["from_stop"] == args.from_stop and t["to_stop"] == args.to_stop:
                    # Parse times and combine with requested date (for simplicity in our mock)
                    dep_t = datetime.time.fromisoformat(t["depart_at"])
                    arr_t = datetime.time.fromisoformat(t["arrive_at"])
                    
                    dep_dt = datetime.datetime.combine(target_date, dep_t)
                    arr_dt = datetime.datetime.combine(target_date, arr_t)
                    
                    if arr_dt < dep_dt:
                        # Crosses midnight
                        arr_dt += datetime.timedelta(days=1)
                        
                    if dep_dt >= depart_after_dt:
                        legs.append(TransitLeg(
                            trip_id=t["trip_id"],
                            from_stop=t["from_stop"],
                            to_stop=t["to_stop"],
                            depart_at=dep_dt,
                            arrive_at=arr_dt,
                            feed_version=t["feed_version"],
                            mode=t["mode"]
                        ))
        return sorted(legs, key=lambda l: l.depart_at)
