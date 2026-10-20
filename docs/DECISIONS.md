# Decisions Log

## Day 3: Foundation
* **State Machine Tools**: Tools are strictly partitioned into "read" (automatically executed) and "write" (paused for human approval).
* **Idempotency**: Implemented `ApprovalQueue` where write tools are mapped with `itinerary_id + step_index + resource_id`.
* **Limits**: Hardcoded circuit breakers: Max steps = 25, Max tokens = 60000, Max cost = $0.05.

## Day 4: End-to-End & Security
* **Drafting Strategy**: Option A (Rule-based drafting only) is selected to bypass LLM variability, keeping testing deterministic and avoiding premature integration of provider logic.
* **Structural Injection Defense**: Wikivoyage and other external text are wrapped in strict `<DATA>...</DATA>` XML-like blocks. The LLM is instructed to treat this as literal data.
* **Audit Heuristics**: Added `detect_injection_signals` that looks for strings like "ignore previous instructions" directly in the fetched text.
* **SSE Streaming**: Implemented `POST /plan` using Server-Sent Events to stream progress (constraints, drafting, violations, awaiting_approval) to the Angular UI.
* **UI**: Created an Angular app under `web/` using `@angular/cli@18` with a simple Timeline Component that parses SSE events and exposes Approve/Reject actions.

## Day 7: Observability & Production Hardening
* **OpenTelemetry Instrumentation**: Added `opentelemetry-api` and `opentelemetry-sdk` runtime dependencies to fulfill Section 5 of AGENTS.md (OpenTelemetry GenAI semantic conventions). Built `core/telemetry.py` recording spans with attributes (`gen_ai.system`, `gen_ai.request.model`, `tripagent.purpose`, `tripagent.step_index`, `tripagent.latency_ms`) across all planner graph transitions.
* **Unified AuditTrail Model**: Refactored `AuditTrail` into a single Pydantic `BaseModel` supporting indexing, appending, and serialization across `core/models.py` and `core/audit.py`.
* **Synchronous Graph Execution**: Provided `submit_sync` on `ApprovalQueue` so LangGraph planner nodes execute synchronously in `graph.invoke()` while supporting streaming asynchronous workflows in FastAPI.
* **Frontend CI Path**: Corrected GitHub Actions `deploy.yml` static build source directory from `frontend` to `web` matching the actual Angular 18 repository layout.

## Day 8: Real LLM Grounding & Trajectory Evaluation (DeepSeek-V4.1-Flash)
* **Tier-Based Model Routing**: Implemented `providers/base.py`, `providers/openai_compatible.py`, and `providers/factory.py` adhering strictly to AGENTS.md Section 1.3.
  - Offline evaluation routes to the `low_cost` tier: **DeepSeek-V4.1-Flash** (API model `deepseek-flash`, $0.14/1M in, $0.28/1M out), providing low latency (~10s) and zero schema drift for structured Pydantic outputs.
  - User-facing path routes to the `western_hosted` tier: OpenAI `gpt-4o-mini` (bring-your-own-key reference implementation).
* **LLM Grounding & Untrusted Context**: Replaced the Day 4 rule-based drafting stub with `draft_itinerary` calling `agenerate_structured`. Candidate venues and GTFS transit legs are injected within `<DATA>...</DATA>` boundary blocks to eliminate prompt injection risks.
* **Deterministic Replanning Loop**: On validator failure, critique is accumulated in state and passed to the next LLM generation cycle (up to 3 replanning attempts).
* **Empirical Trajectory Evaluation**: Evaluated 20 realistic scenarios with DeepSeek-V4.1-Flash (`eval_runs/run_deepseek_6babf91_20261020T023119Z.jsonl`):
  - **Hallucination Rate**: 0.0% (0 fabricated venue IDs, station IDs, or prices verified by `FixtureSource`).
  - **Constraint Satisfaction**: 95.7%
  - **Feasibility Rate**: 55.0%
  - **Honest Infeasibility Rate**: 10.0%
  - **Cost per Task**: $0.0027 (0.27 cents / itinerary)
* **Stealth Schedule Relaxation (Failure Mode Analysis)**: 35.0% false-feasible rate occurs when users request round-trip travel where the GTFS schedule only contains one-way legs. The LLM schedules the single available leg within budget, which passes validators but drops the return journey constraint. Documented in `docs/FAILURE-MODES.md`.

