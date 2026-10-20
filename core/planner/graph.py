from __future__ import annotations

import asyncio
import concurrent.futures
import datetime
import json
import time
from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from retrieval_core.models import Query, ScoredHit  # type: ignore[import-untyped]

from adapters.gtfs import GTFSAdapter
from adapters.static_retriever import StaticRetriever
from core.approval import get_approval_queue
from core.audit import AuditRecord, AuditTrail
from core.models import Itinerary, PlanResult, Violation
from core.planner.abort import create_abort_node
from core.planner.events import emit_event
from core.planner.limits import CircuitBreakers, LimitConfig
from core.planner.state import PlannerState
from core.telemetry import trace_genai_span
from core.untrusted import (
    detect_injection_signals,
    format_for_context,
    wrap_retrieved,
)
from core.validators.budget import BudgetValidator
from core.validators.connectivity import ConnectivityValidator
from core.validators.geography import GeographyValidator
from core.validators.opening_hours import OpeningHoursValidator
from providers.base import LLMProvider


def run_coro_sync(coro_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run an async coroutine safely whether called from a sync thread or inside an active event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro_fn(*args, **kwargs))).result()
    else:
        return asyncio.run(coro_fn(*args, **kwargs))


def create_planner_graph(
    breakers: CircuitBreakers,
    provider: LLMProvider | None = None,
    retriever: Any | None = None,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """
    Builds the LangGraph travel planning agent state graph.
    Injects deterministic validators, untrusted content grounding, and LLM drafting/replanning.
    """
    if retriever is None:
        retriever = StaticRetriever()
    gtfs_adapter = GTFSAdapter()

    def parse_constraints(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("parse_constraints", purpose="constraint_parsing", step_index=state.get("step_count", 0)):
            req = state.get("request")
            constraints = req.constraints if req else []
            ev = emit_event("constraints_parsed", {"constraints": [c.model_dump() for c in constraints]})
            events = state.get("sse_events", []) + [ev.model_dump()]
            return {"constraints": constraints, "sse_events": events}

    def retrieve(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("retrieve", purpose="grounding_retrieval", step_index=state.get("step_count", 0)):
            req = state.get("request")
            hits: list[ScoredHit] = []
            grounded_context = ""
            events = list(state.get("sse_events", []))

            if req:
                # Retrieve matching venue hits
                query = Query(text=req.request_text, user_id=None)
                hits = run_coro_sync(retriever.retrieve, query, 10)

                # Collect documents for matching venues
                untrusted_items: list[Any] = []
                retrieved_venue_ids = {h.doc_id for h in hits}
                for doc in getattr(retriever, "documents", []):
                    if doc.get("venue_id") in retrieved_venue_ids or len(untrusted_items) < 6:
                        price_eur = 0.0
                        if doc.get("prices"):
                            price_eur = float(doc["prices"][0].get("amount", 0.0))
                        venue_payload = {
                            "type": "venue",
                            "venue_id": doc["venue_id"],
                            "name": doc["name"],
                            "city": doc["city"],
                            "coord": doc.get("coord", {}),
                            "cost": price_eur,
                            "source_id": doc.get("source_id", "wikivoyage"),
                            "source_version": doc.get("source_version", "2024-06-curated"),
                        }
                        untrusted_items.append(
                            wrap_retrieved(
                                json.dumps(venue_payload),
                                source_id=doc.get("source_id", "wikivoyage"),
                                source_version=doc.get("source_version", "2024-06-curated"),
                            )
                        )

                # Collect transit legs
                all_transit_legs = gtfs_adapter.all_legs()
                for leg in all_transit_legs:
                    leg_payload = {
                        "type": "transit",
                        "trip_id": leg["trip_id"],
                        "from_stop": leg["from_stop"],
                        "to_stop": leg["to_stop"],
                        "depart_at": leg["depart_at"],
                        "arrive_at": leg["arrive_at"],
                        "mode": leg.get("mode", "train"),
                        "cost": float(leg.get("price", 0.0)),
                        "feed_version": leg.get("feed_version", "2024-GTFS"),
                    }
                    untrusted_items.append(
                        wrap_retrieved(
                            json.dumps(leg_payload),
                            source_id=leg["trip_id"],
                            source_version=leg.get("feed_version", "2024-GTFS"),
                        )
                    )

                # Check for prompt injection heuristic signals
                signals = detect_injection_signals(req.request_text)
                if signals:
                    audit = state.get("audit_trail") or AuditTrail()
                    audit.append(
                        AuditRecord(
                            step_index=state.get("step_count", 0),
                            action_type="security_heuristic",
                            tool_name="detect_injection_signals",
                            source_id="input_filter",
                            source_version="1.0",
                            duration_ms=1,
                            tokens_in=0,
                            tokens_out=0,
                            cost_usd=0.0,
                            validator_failures=len(signals),
                            timestamp=datetime.datetime.now(datetime.UTC),
                        )
                    )

                grounded_context = format_for_context(untrusted_items)

            ev = emit_event("retrieving", {"hits_count": len(hits)})
            events.append(ev.model_dump())
            return {
                "retrieved_hits": hits,
                "grounded_context": grounded_context,
                "sse_events": events,
            }

    def draft_itinerary(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("draft_itinerary", purpose="drafting", step_index=state.get("step_count", 0)):
            req = state.get("request")
            events = list(state.get("sse_events", []))

            # If no provider injected or no request, fallback to existing stub
            if provider is None or req is None:
                existing_itin = state.get("itinerary")
                if existing_itin:
                    ev = emit_event("drafting", {"itinerary": existing_itin.model_dump(mode="json")})
                    events.append(ev.model_dump())
                    return {"itinerary": existing_itin, "sse_events": events}

                itin = Itinerary(
                    itinerary_id="stub-itin",
                    steps=[],
                    total_cost=0.0,
                    currency="EUR",
                )
                ev = emit_event("drafting", {"itinerary": itin.model_dump(mode="json")})
                events.append(ev.model_dump())
                return {"itinerary": itin, "sse_events": events}

            # Build grounded system prompt
            system_prompt = (
                "You are TripAgent, a precision travel planning agent.\n"
                "Your task is to draft a realistic, conflict-free travel itinerary as a JSON object adhering strictly to the schema.\n\n"
                "CRITICAL RULES & CONSTRAINTS:\n"
                "1. STRICT GROUNDING: You MUST ONLY select venues and transit legs that appear in the provided UNTRUSTED DATA context.\n"
                "   - For visit steps: use the exact venue_id, name, city, coord, and cost from a venue in the context.\n"
                "   - For transit steps: use the exact trip_id, from_stop, to_stop, mode, and feed_version from a transit leg in the context.\n"
                "   - DO NOT fabricate, hallucinate, or alter venue IDs, station names, trip IDs, or prices under any circumstances.\n"
                "2. SCHEDULE & TIMING:\n"
                "   - The trip starts on Tuesday, June 4, 2024 (2024-06-04). Day 1 is 2024-06-04. Day 2 is 2024-06-05, etc.\n"
                "   - All visits must take place between 09:00:00 and 18:00:00.\n"
                "   - Never schedule a visit on a Monday (weekday=0) because institutions are closed on Mondays.\n"
                "   - Visits must NOT overlap in time. Ensure next step starts_at >= previous step ends_at.\n"
                "   - Consecutive visits within the same city must allow sufficient travel/walking time (at least 30 minutes between ends_at and next starts_at).\n"
                "3. INTER-CITY TRANSIT:\n"
                "   - If consecutive visits are in different cities, you MUST include a transit step between them with a valid leg from the candidates.\n"
                "4. BUDGET:\n"
                "   - Total itinerary cost must NOT exceed the user's budget.\n"
                "   - If the user's budget is genuinely impossible (e.g. required transit costs more than the total budget), do NOT invent fake zero prices or fake discounts. Provide your closest grounded attempt so our deterministic validators can detect and report the infeasibility honestly.\n"
                "5. EXCLUDED MODES:\n"
                "   - Do NOT select transit modes that the user has explicitly excluded.\n"
                "6. FORMATTING:\n"
                "   - itinerary_id should be 'itin-1'. currency must be 'EUR'.\n"
                "   - steps must have kind 'visit' or 'transit', with step_index starting at 1.\n"
            )

            # Replan critique if previous validation produced violations
            violations = state.get("violations", [])
            if violations:
                critique_lines = [f"- {v.explanation} (Constraint breached: {v.breached_constraint})" for v in violations]
                system_prompt += (
                    "\n\nPREVIOUS ATTEMPT FAILED DETERMINISTIC VALIDATION:\n"
                    "The previous itinerary failed with the following violations:\n"
                    + "\n".join(critique_lines)
                    + "\nYou MUST adjust the itinerary to fix these violations. If a constraint is impossible to meet, do not hallucinate."
                )

            excluded_modes = [c.value for c in req.constraints if c.kind == "exclude_mode"]
            user_prompt = (
                f"Trip Request: {req.request_text}\n"
                f"Days: {req.days}\n"
                f"Budget: {req.budget} EUR\n"
                f"Party Size: {req.party_size}\n"
                f"Excluded Transit Modes: {excluded_modes}\n\n"
                f"{state.get('grounded_context', '')}"
            )

            start_t = time.perf_counter()
            try:
                itin, tokens_in, tokens_out, cost_usd = run_coro_sync(
                    provider.agenerate_structured,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=Itinerary,
                    purpose="itinerary_drafting",
                    temperature=0.2,
                )
            except (ValueError, RuntimeError, OSError, TimeoutError, KeyError):
                # Fallback to minimal grounded attempt on parse or API failure
                itin = Itinerary(
                    itinerary_id="fallback-itin",
                    steps=[],
                    total_cost=0.0,
                    currency="EUR",
                )
                tokens_in, tokens_out, cost_usd = 0, 0, 0.0

            duration_ms = int((time.perf_counter() - start_t) * 1000)

            audit = state.get("audit_trail") or AuditTrail()
            audit.append(
                AuditRecord(
                    step_index=state.get("step_count", 0),
                    action_type="draft_itinerary",
                    tool_name="agenerate_structured",
                    source_id=getattr(provider, "provider_name", "llm"),
                    source_version=getattr(provider, "model", "1.0"),
                    duration_ms=duration_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                    validator_failures=len(violations),
                    timestamp=datetime.datetime.now(datetime.UTC),
                )
            )

            total_tokens = state.get("total_tokens", 0) + tokens_in + tokens_out
            total_cost = state.get("total_cost", 0.0) + cost_usd
            step_count = state.get("step_count", 0) + 1

            ev = emit_event("drafting", {"itinerary": itin.model_dump(mode="json")})
            events.append(ev.model_dump())

            return {
                "itinerary": itin,
                "audit_trail": audit,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "step_count": step_count,
                "sse_events": events,
            }

    def validate(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("validate", purpose="deterministic_validation", step_index=state.get("step_count", 0)):
            itin = state.get("itinerary")
            req = state.get("request")

            events = list(state.get("sse_events", []))
            events.append(emit_event("validating", {}).model_dump())

            if not itin or not req:
                return {"violations": [], "sse_events": events}

            validators: list[Any] = [
                BudgetValidator(),
                OpeningHoursValidator(),
                GeographyValidator(),
                ConnectivityValidator(),
            ]

            violations = []
            for v in validators:
                violations.extend(v.validate(itin, req))

            # Also validate excluded modes constraint
            if req.constraints:
                excluded_modes = {c.value.lower() for c in req.constraints if c.kind == "exclude_mode"}
                if excluded_modes:
                    for step in itin.steps:
                        if step.kind == "transit" and step.leg and step.leg.mode.lower() in excluded_modes:
                            violations.append(
                                Violation(
                                    validator="mode_validator",
                                    severity="hard",
                                    step_index=step.step_index,
                                    explanation=f"Transit mode {step.leg.mode} is excluded by user constraints.",
                                    breached_constraint="exclude_mode",
                                )
                            )

            if violations:
                events.append(
                    emit_event("violation_found", {"violations": [v.model_dump(mode="json") for v in violations]}).model_dump()
                )

            return {"violations": violations, "sse_events": events}

    def replan(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("replan", purpose="replanning", step_index=state.get("step_count", 0)):
            count = state.get("replan_count", 0) + 1
            audit = state.get("audit_trail") or AuditTrail()
            audit.append(
                AuditRecord(
                    step_index=state.get("step_count", 0),
                    action_type="replan",
                    tool_name="planner_replan",
                    source_id="graph",
                    source_version="1.0",
                    duration_ms=1,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    validator_failures=len(state.get("violations", [])),
                    timestamp=datetime.datetime.now(datetime.UTC),
                )
            )
            ev = emit_event("replanning", {"replan_count": count})
            events = list(state.get("sse_events", [])) + [ev.model_dump()]
            return {"replan_count": count, "audit_trail": audit, "sse_events": events}

    def execute_writes(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("execute_writes", purpose="write_execution", step_index=state.get("step_count", 0)):
            itin = state.get("itinerary")
            events = list(state.get("sse_events", []))
            if not itin:
                return {"pending_actions": [], "sse_events": events}

            queue = get_approval_queue()
            pending = []

            for i, step in enumerate(itin.steps):
                step_type = getattr(step, "kind", None) or (step.get("type") if isinstance(step, dict) else None)
                if step_type == "transit":
                    leg = getattr(step, "leg", None)
                    trip_id = leg.trip_id if leg else (step.get("trip_id") if isinstance(step, dict) else None)
                    key = f"{itin.itinerary_id}-{i}-book"
                    action = queue.submit_sync("book_transit", {"trip_id": trip_id}, key)
                    if action.status == "pending":
                        pending.append(action)
                    elif action.status == "rejected":
                        events.append(
                            emit_event(
                                "violation_found",
                                {"violations": [{"rule": "approval", "detail": "User rejected booking"}]},
                            ).model_dump()
                        )
                        return {
                            "status": "infeasible",
                            "violations": [{"rule": "approval", "detail": "User rejected booking"}],
                            "sse_events": events,
                        }

            if pending:
                events.append(emit_event("awaiting_approval", {"pending_actions": [p.model_dump() for p in pending]}).model_dump())
                return {"status": "awaiting_approval", "pending_actions": pending, "sse_events": events}
            return {"pending_actions": [], "sse_events": events}

    def finalise(state: PlannerState) -> dict[str, Any]:
        with trace_genai_span("finalise", purpose="finalisation", step_index=state.get("step_count", 0)):
            status = state.get("status")
            valid_status: Literal["finalised", "infeasible", "aborted"] = "finalised"
            if state.get("violations"):
                valid_status = "infeasible"
            elif status in ["finalised", "infeasible", "aborted"]:
                valid_status = status  # type: ignore[assignment]

            result = PlanResult(
                status=valid_status,
                itinerary=state.get("itinerary"),
                violations=state.get("violations", []),
                audit_trail=state.get("audit_trail") if state.get("audit_trail") else AuditTrail(),
            )

            events = list(state.get("sse_events", []))
            if valid_status == "finalised":
                events.append(emit_event("finalised", {"plan_result": result.model_dump(mode="json")}).model_dump())
            elif valid_status == "infeasible":
                events.append(emit_event("infeasible", {"plan_result": result.model_dump(mode="json")}).model_dump())

            return {"plan_result": result, "status": valid_status, "sse_events": events}

    def wrap_abort(brk: CircuitBreakers) -> Callable[[PlannerState], dict[str, Any]]:
        node = create_abort_node(brk)

        def wrapped(state: PlannerState) -> dict[str, Any]:
            with trace_genai_span("abort", purpose="circuit_breaker_abort", step_index=state.get("step_count", 0)):
                res = node(state)
                ev = emit_event("aborted", {"which_limit": res.get("which_limit")})
                events = list(state.get("sse_events", [])) + [ev.model_dump()]
                res["sse_events"] = events
                return res

        return wrapped

    builder = StateGraph(PlannerState)

    builder.add_node("parse_constraints", parse_constraints)
    builder.add_node("retrieve", retrieve)
    builder.add_node("draft_itinerary", draft_itinerary)
    builder.add_node("validate", validate)
    builder.add_node("replan", replan)
    builder.add_node("execute_writes", execute_writes)
    builder.add_node("finalise", finalise)
    builder.add_node("abort", wrap_abort(breakers))  # type: ignore[arg-type]

    def check_limits_or_next(next_node: str) -> Callable[[PlannerState], str]:
        def _check(state: PlannerState) -> str:
            limit = breakers.check(
                state.get("step_count", 0),
                state.get("total_tokens", 0),
                state.get("total_cost", 0.0),
            )
            if limit:
                return "abort"
            return next_node

        return _check

    builder.set_entry_point("parse_constraints")

    builder.add_conditional_edges("parse_constraints", check_limits_or_next("retrieve"))
    builder.add_conditional_edges("retrieve", check_limits_or_next("draft_itinerary"))
    builder.add_conditional_edges("draft_itinerary", check_limits_or_next("validate"))

    def after_validate(state: PlannerState) -> str:
        limit = breakers.check(
            state.get("step_count", 0),
            state.get("total_tokens", 0),
            state.get("total_cost", 0.0),
        )
        if limit:
            return "abort"

        violations = state.get("violations", [])
        if violations:
            if state.get("replan_count", 0) < breakers.config.max_replans:
                return "replan"
            return "finalise"
        return "execute_writes"

    builder.add_conditional_edges("validate", after_validate)
    builder.add_conditional_edges("replan", check_limits_or_next("draft_itinerary"))

    def after_writes(state: PlannerState) -> str:
        return "finalise"

    builder.add_conditional_edges("execute_writes", after_writes)

    builder.add_edge("finalise", END)
    builder.add_edge("abort", END)

    return builder.compile()


# Global graph cache
_graph: CompiledStateGraph | None = None  # type: ignore[type-arg]


def get_graph(provider: LLMProvider | None = None) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Retrieve or create the compiled planner graph. Injects default provider if available."""
    global _graph
    if provider is not None:
        breakers = CircuitBreakers(LimitConfig())
        return create_planner_graph(breakers, provider=provider)

    if _graph is None:
        from app.settings import settings
        from providers.factory import create_provider

        active_provider: LLMProvider | None = None
        try:
            tier: Literal["low_cost", "western_hosted"] = (
                "western_hosted"
                if settings.default_ai_provider in ["gemini", "openai"]
                else "low_cost"
            )
            key = (
                settings.gemini_api_key
                or settings.openai_api_key
                or settings.deepseek_api_key
            )
            if key and key.strip():
                active_provider = create_provider(tier, settings=settings)
        except (ValueError, KeyError, AttributeError, OSError):
            active_provider = None

        breakers = CircuitBreakers(LimitConfig())
        _graph = create_planner_graph(breakers, provider=active_provider)

    return _graph
