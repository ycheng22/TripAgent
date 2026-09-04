from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
from core.models import TripRequest, Itinerary
from core.planner.graph import get_graph
from core.approval import get_approval_queue
from pydantic import BaseModel

app = FastAPI(title="TripAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

from fastapi.responses import StreamingResponse
import json
import asyncio

@app.post("/plan")
async def plan_trip(user_input: TripRequest):
    graph = get_graph()
    
    async def event_generator():
        try:
            # We will use graph.astream
            async for step in graph.astream({"user_input": user_input}, stream_mode="values"):
                # step is the current state
                events = step.get("sse_events", [])
                if events:
                    # yield the latest event
                    # the graph appends, so we just take the last one or two
                    # Actually astream("values") yields the whole state every time a node finishes.
                    # We can keep track of how many events we have seen to only yield new ones.
                    pass
        except Exception as e:
            yield f"data: {json.dumps({'event_type': 'error', 'payload': {'detail': str(e)}})}\n\n"
            
    # Wait, the event generation requires tracking seen events. Let's do it cleanly.
    async def clean_event_generator():
        seen_count = 0
        try:
            async for step in graph.astream({"user_input": user_input}, stream_mode="values"):
                events = step.get("sse_events", [])
                while seen_count < len(events):
                    ev = events[seen_count]
                    # Format as Server-Sent Event
                    yield f"event: {ev['event_type']}\ndata: {json.dumps(ev['payload'])}\n\n"
                    seen_count += 1
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(clean_event_generator(), media_type="text/event-stream")


@app.get("/approvals")
async def list_approvals():
    queue = get_approval_queue()
    actions = await queue.list_pending()
    return {"actions": [a.model_dump() for a in actions]}

class RejectRequest(BaseModel):
    reason: str

@app.post("/approvals/{action_id}/approve")
async def approve_action(action_id: str):
    queue = get_approval_queue()
    try:
        action = await queue.approve(action_id)
        return action.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Action not found")

@app.post("/approvals/{action_id}/reject")
async def reject_action(action_id: str, req: RejectRequest):
    queue = get_approval_queue()
    try:
        constraint = await queue.reject(action_id, req.reason)
        return {"status": "rejected", "constraint": constraint.model_dump()}
    except KeyError:
        raise HTTPException(status_code=404, detail="Action not found")
