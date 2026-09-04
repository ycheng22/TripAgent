from pydantic import BaseModel
import datetime
from typing import Any

class SSEEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime.datetime

def emit_event(event_type: str, payload: dict[str, Any]) -> SSEEvent:
    return SSEEvent(
        event_type=event_type,
        payload=payload,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
