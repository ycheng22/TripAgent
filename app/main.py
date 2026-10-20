from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.settings import settings
from core.approval import get_approval_queue
from core.models import TripRequest
from core.planner.graph import get_graph

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

import asyncio
import json

from fastapi import Request
from fastapi.responses import StreamingResponse

_demo_cache = None

def get_demo_cache():
    global _demo_cache
    if _demo_cache is None:
        try:
            with open("data/demo_cache.json", "r", encoding="utf-8") as f:
                _demo_cache = json.load(f)
        except FileNotFoundError:
            _demo_cache = {}
    return _demo_cache

@app.post("/plan")
async def plan_trip(request: Request, user_input: TripRequest):
    req_text = user_input.request_text.strip().lower()
    cache = get_demo_cache()
    
    if req_text in cache:
        async def replay_generator():
            for ev in cache[req_text]:
                # Fake latency for animation
                await asyncio.sleep(0.5)
                yield f"event: {ev['event_type']}\ndata: {json.dumps(ev['payload'])}\n\n"
        return StreamingResponse(replay_generator(), media_type="text/event-stream")
        
    from core.telemetry import trace_genai_span
    graph = get_graph()
    
    async def clean_event_generator():
        seen_count = 0
        try:
            with trace_genai_span("sse_plan_stream", purpose="user_plan_stream"):
                async for step in graph.astream({"request": user_input}, stream_mode="values"):
                    events = step.get("sse_events", [])
                    while seen_count < len(events):
                        ev = events[seen_count]
                        yield f"event: {ev['event_type']}\ndata: {json.dumps(ev['payload'], default=str)}\n\n"
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
