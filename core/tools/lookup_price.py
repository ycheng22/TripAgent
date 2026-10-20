import asyncio
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from adapters.wikivoyage import WikivoyageAdapter
from core.models import Price


class LookupPriceArgs(BaseModel):
    item_id: str
    category: str

class LookupPriceTool:
    name: str = "lookup_price"
    description: str = "Lookup the price of an item (venue admission or transit ticket)."
    args_model = LookupPriceArgs
    access: Literal["read"] = "read"

    def execute(self, args: LookupPriceArgs) -> Price | None:
        # Check venues first
        adapter = WikivoyageAdapter()
        loop = asyncio.new_event_loop()
        try:
            doc = loop.run_until_complete(adapter.get_document(args.item_id))
            if doc and "prices" in doc.metadata:
                for p in doc.metadata["prices"]:
                    if p["category"] == args.category:
                        return Price(item_id=args.item_id, category=args.category, amount=p["amount"], currency=p["currency"])
        finally:
            loop.close()
            
        # Check transit legs
        path = Path("data/gtfs/transit_legs.json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for t in data:
                if t["trip_id"] == args.item_id and "price" in t and "currency" in t:
                    return Price(item_id=args.item_id, category=args.category, amount=t["price"], currency=t["currency"])
                        
        return None
