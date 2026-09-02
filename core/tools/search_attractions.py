from pydantic import BaseModel
from typing import Literal
from core.models import Venue, Coordinate

class SearchAttractionsArgs(BaseModel):
    city: str
    query: str
    top_k: int

class SearchAttractionsTool:
    name: str = "search_attractions"
    description: str = "Search for attractions in a given city"
    args_model = SearchAttractionsArgs
    access: Literal["read"] = "read"

    def execute(self, args: SearchAttractionsArgs) -> list[Venue]:
        # Stub implementation
        return [
            Venue(
                venue_id=f"stub-{args.city}-1",
                name=f"{args.query} in {args.city}",
                city=args.city,
                coord=Coordinate(lat=52.5200, lon=13.4050),
                source_id="wikivoyage",
                source_version="2024-01-stub"
            )
        ]
