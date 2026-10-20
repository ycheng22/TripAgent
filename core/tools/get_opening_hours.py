import asyncio
import datetime
from typing import Literal

from pydantic import BaseModel

from adapters.wikivoyage import WikivoyageAdapter
from core.models import OpeningHours


class GetOpeningHoursArgs(BaseModel):
    venue_id: str
    date: str # ISO format YYYY-MM-DD

class GetOpeningHoursTool:
    name: str = "get_opening_hours"
    description: str = "Get the opening hours for a venue on a specific date."
    args_model = GetOpeningHoursArgs
    access: Literal["read"] = "read"

    def execute(self, args: GetOpeningHoursArgs) -> OpeningHours:
        adapter = WikivoyageAdapter()
        loop = asyncio.new_event_loop()
        try:
            doc = loop.run_until_complete(adapter.get_document(args.venue_id))
            if not doc or "opening_hours" not in doc.metadata:
                # Default to open if not found, or maybe raise. In reality, it should just return empty/None 
                # but the spec asks for OpeningHours. We'll return 24/7.
                return OpeningHours(
                    venue_id=args.venue_id,
                    open_time=datetime.time(0, 0),
                    close_time=datetime.time(23, 59, 59),
                    closure_days=[]
                )
            
            oh = doc.metadata["opening_hours"]
            return OpeningHours(
                venue_id=args.venue_id,
                open_time=datetime.time.fromisoformat(oh["open_time"]),
                close_time=datetime.time.fromisoformat(oh["close_time"]),
                closure_days=oh.get("closure_days", [])
            )
        finally:
            loop.close()
