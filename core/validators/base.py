from typing import Protocol

from core.models import Itinerary, TripRequest, Violation


class Validator(Protocol):
    name: str

    def validate(self, itinerary: Itinerary, request: TripRequest) -> list[Violation]:
        ...
