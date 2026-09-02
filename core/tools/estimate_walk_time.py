from pydantic import BaseModel
from typing import Literal
import math
from core.models import Coordinate

class EstimateWalkTimeArgs(BaseModel):
    coord_a: Coordinate
    coord_b: Coordinate
    speed_kmh: float = 4.5

class EstimateWalkTimeResult(BaseModel):
    seconds: int
    source_id: str
    source_version: str

class EstimateWalkTimeTool:
    name: str = "estimate_walk_time"
    description: str = "Estimate walking time between two coordinates in seconds"
    args_model = EstimateWalkTimeArgs
    access: Literal["read"] = "read"

    def execute(self, args: EstimateWalkTimeArgs) -> EstimateWalkTimeResult:
        # Haversine formula
        R = 6371.0
        lat1 = math.radians(args.coord_a.lat)
        lon1 = math.radians(args.coord_a.lon)
        lat2 = math.radians(args.coord_b.lat)
        lon2 = math.radians(args.coord_b.lon)
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        seconds = int((distance / args.speed_kmh) * 3600)
        
        return EstimateWalkTimeResult(
            seconds=seconds,
            source_id="haversine",
            source_version="1.0"
        )
