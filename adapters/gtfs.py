import json
from pathlib import Path
from typing import Any


class GTFSAdapter:
    def __init__(self, data_path: Path = Path("data/gtfs/transit_legs.json")):
        self.data_path = data_path
        self.legs: list[dict[str, Any]] = []
        if self.data_path.exists():
            try:
                self.legs = json.loads(self.data_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.legs = []

    def all_legs(self) -> list[dict[str, Any]]:
        return list(self.legs)

    def get_leg(self, trip_id: str) -> dict[str, Any] | None:
        for leg in self.legs:
            if leg.get("trip_id") == trip_id:
                return leg
        return None
