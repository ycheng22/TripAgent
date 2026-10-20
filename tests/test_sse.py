from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_sse_streaming_endpoint():
    # Test that /plan returns SSE
    with client.stream("POST", "/plan", json={
        "request_text": "I want to visit Paris for 2 days. We are a couple, and we have a budget of 300 EUR. We just want to see the Eiffel Tower and maybe a museum.",
        "constraints": [],
        "party_size": 2,
        "budget": 300.0,
        "days": 2
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
