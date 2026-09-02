from pydantic import BaseModel
from typing import Literal
from core.models import Price

class LookupPriceArgs(BaseModel):
    item_id: str
    category: str

class LookupPriceResult(BaseModel):
    price: Price | None

class LookupPriceTool:
    name: str = "lookup_price"
    description: str = "Lookup price for an item"
    args_model = LookupPriceArgs
    access: Literal["read"] = "read"

    def execute(self, args: LookupPriceArgs) -> LookupPriceResult:
        # Stub implementation
        db = {
            "stub-trip-1": 15.0,
            "stub-berlin-1": 20.0
        }
        
        if args.item_id in db:
            return LookupPriceResult(
                price=Price(
                    item_id=args.item_id,
                    category=args.category,
                    amount=db[args.item_id],
                    currency="EUR"
                )
            )
        return LookupPriceResult(price=None)
