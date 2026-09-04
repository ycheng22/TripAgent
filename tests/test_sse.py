import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_sse_streaming_endpoint():
    # Test that /plan returns SSE
    with client.stream("POST", "/plan", json={
        "request_text": "5 days / €1200 / two people / no long-distance coaches",
        "constraints": [],
        "party_size": 2,
        "budget": 1200.0,
        "days": 5
    }) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        events = []
        for line in response.iter_lines():
            if line.startswith("event: "):
                events.append(line.replace("event: ", ""))
                
        # In our mock logic, we should see these events in order:
        assert "constraints_parsed" in events
        assert "retrieving" in events
        assert "drafting" in events
        assert "validating" in events
        
        # It should either be finalised, infeasible, or awaiting_approval
        assert any(e in events for e in ["finalised", "infeasible", "awaiting_approval"])
