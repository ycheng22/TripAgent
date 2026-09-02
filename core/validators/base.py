from typing import Protocol
from core.models import Itinerary, Violation, TripRequest

class Validator(Protocol):
    name: str

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        ...
