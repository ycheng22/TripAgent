# Decisions Log

## Deployment: Cloud Run and Cloudflare Pages
* **Immutable backend artifact**: TripAgent builds a Python 3.12 container in GitHub Actions and publishes it to Artifact Registry with the Git SHA as its only deploy tag. Cloud Run deploys that immutable image, rather than a source deployment, so a running revision can be traced to an exact commit and rolled back.
* **Runtime configuration**: Non-secret deployment settings are injected from GitHub Actions repository variables. Database and model-provider credentials are stored in Google Secret Manager and mounted into Cloud Run as environment variables. `app/settings.py` remains the application’s sole environment reader.
* **Frontend API configuration**: The Angular production environment file is generated only during CI from the Cloud Run deployment output. It is ignored by Git, leaving the local development API URL unchanged and preventing a mutable `*.run.app` endpoint from entering frontend source.
* **Frontend build budgets**: The component-style production error budget is 5 kB. This accommodates the measured 4.61 kB largest current component stylesheet while retaining a warning threshold at 4 kB and preventing unbounded style growth.
* **Deployment topology and cost**: The static Angular build is uploaded directly to Cloudflare Pages. The API remains on its generated `*.run.app` address; it has no custom domain or Cloudflare proxy. Cloud Run uses `min-instances=0` and `max-instances=3`, while the scheduled keepalive calls database-free `GET /ping`.

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
* **Demo Cache & UI Itinerary Rendering**:
  - Fixed precompute script (`scripts/precompute_demo_scenarios.py`) passing `{"request": req}` to LangGraph instead of deprecated `user_input`.
  - Recomputed all 8 demo scenarios from `docs/DEMO-SCENARIOS.md` with authentic DeepSeek-V4.1-Flash runs and persisted them to `data/demo_cache.json`.
  - Enhanced `TimelineComponent` (`web/src/app/timeline/`) with dedicated itinerary cards rendering day chips, time ranges, venue names, Wikivoyage IDs, transit route information, and ticket prices instead of displaying raw JSON or only total cost.

## Day 9: Neon DB Presets, 20 Preset Landing Cards, Rate Limiting, and Gemini 3.5 Flash-Lite
* **Neon DB Scenario Persistence & Replay (`asyncpg`)**:
  - Saved all 20 evaluated benchmark scenarios from `eval_runs/run_deepseek_6babf91_20261020T023119Z.jsonl` into Neon PostgreSQL (`tripagent` project/db) within the `preset_scenarios` table.
  - Added `asyncpg>=0.29.0` runtime dependency (documented in `DECISIONS.md` per AGENTS.md Section 1).
  - Implemented async repository in `core/db.py` with graceful fallback to `data/preset_cache.json` if Neon DB is temporarily sleeping or unreachable.
  - Adhered strictly to AGENTS.md Rule 3: `/healthz` **never** touches PostgreSQL, preventing compute spin-up during keepalive polling.
* **Landing Page Preset Cards (20 Scenarios)**:
  - Display 20 preset cards on the landing page grouped by category (`All`, `Romantic`, `Transit`, `Budget`, `Accessibility`, `Family`, `Culture`, `Outdoor`, `Food & Wine`).
  - Cards highlight destination, days, budget, party size, and expected feasibility.
  - Clicking any card triggers instant SSE replay loaded from Neon DB, demonstrating the live planning experience with zero LLM API costs.
* **Rate Limiting (5 calls / 10 minutes)**:
  - Implemented in-memory sliding-window rate limiter in `core/rate_limit.py` to protect the $20 monthly budget against abuse.
  - Custom/new scenarios are bounded to 5 live calls per 10 minutes per IP (`RATE_LIMIT_CALLS=5`, `RATE_LIMIT_WINDOW_SECONDS=600`).
  - Breaching the limit emits a clean `rate_limit_exceeded` event and helpful UI banner without crashing the server.
  - Preset scenarios bypass the rate limiter entirely.
* **Default AI Model (Gemini 3.5 Flash-Lite & Failover)**:
  - Configured `DEFAULT_AI_MODEL=gemini-3.5-flash-lite` and `DEFAULT_AI_PROVIDER=gemini` in `app/settings.py` and `.env.example`.
  - Implemented `FailoverProvider` in `providers/factory.py` that gracefully routes calls to OpenAI `gpt-4o-mini` (with `deepseek-flash` secondary fallback) if the Gemini quota is exhausted (HTTP 402/429), maintaining high availability without user disruption.


