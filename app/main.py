import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.settings import settings
from core.approval import get_approval_queue
from core.db import get_all_presets_meta, get_preset_events
from core.models import TripRequest
from core.planner.graph import get_graph
from core.rate_limit import check_rate_limit, get_client_ip, record_live_call
from core.telemetry import trace_genai_span

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
    """Liveness probe. MUST NOT touch the database (AGENTS.md Section 3)."""
    return {"status": "ok"}


@app.get("/api/presets")
@app.get("/presets")
async def list_presets():
    """Return metadata cards for all 20 evaluated preset scenarios."""
    presets = await get_all_presets_meta(settings.database_url)
    return {"presets": presets, "count": len(presets)}


@app.post("/plan")
async def plan_trip(request: Request, user_input: TripRequest):
    req_text = user_input.request_text.strip().lower()

    # 1. Check if this matches one of our 20 precomputed presets (from Neon DB or cache)
    preset_events = await get_preset_events(req_text, settings.database_url)

    if preset_events:
        async def replay_generator():
            for ev in preset_events:
                # Authentic pacing to showcase the reasoning progression
                await asyncio.sleep(0.18)
                yield f"event: {ev['event_type']}\ndata: {json.dumps(ev['payload'], default=str)}\n\n"

        return StreamingResponse(replay_generator(), media_type="text/event-stream")

    # 2. Free-form / custom scenario: enforce rate limiting (5 live calls per 10 minutes)
    client_ip = get_client_ip(
        dict(request.headers),
        request.client.host if request.client else "127.0.0.1",
    )
    allowed, _remaining, retry_after = check_rate_limit(client_ip)

    if not allowed:
        async def rate_limited_generator():
            payload = {
                "detail": (
                    f"Rate limit reached: Maximum 5 live AI generation calls allowed every 10 minutes. "
                    f"Please select one of the 20 precomputed preset scenarios to test without limits, "
                    f"or try again in {retry_after}s."
                ),
                "retry_after": retry_after,
                "client_ip": client_ip,
            }
            yield f"event: rate_limit_exceeded\ndata: {json.dumps(payload)}\n\n"
            yield f"event: aborted\ndata: {json.dumps({'which_limit': 'rate_limit', 'detail': payload['detail']})}\n\n"

        return StreamingResponse(rate_limited_generator(), media_type="text/event-stream")

    # Record this live call against client IP quota
    record_live_call(client_ip)

    # 3. Execute live LangGraph planning
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
        except Exception as e:  # noqa: BLE001
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
