# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-02

### Added
- **Core Foundations (Phase 1):**
  - Project scaffolding using `uv` with dependencies locked, including `retrieval-core` (v0.2.0).
  - Domain models including `Coordinate`, `Constraint`, `TripRequest`, `Venue`, `TransitLeg`, `ItineraryStep`, `Itinerary`, `Violation`, `PlanResult`, and `AuditRecord`.
  - Tool layer with strict protocol defining read/write access and required `idempotency_key` implementations for write tools (`hold_reservation`, `book_transit`, `send_confirmation`).
  - Governance mechanisms with `AuditTrail` logging and `CircuitBreakers` (enforcing max steps, max tokens, max cost, and max replans limits).
  - LangGraph-based state machine (`core/planner/graph.py`) modeling the planning loop (`parse_constraints`, `retrieve`, `draft_itinerary`, `validate`, `replan`, `finalise`, `abort`).
  - Stub `WikivoyageAdapter` structurally conforming to `DocumentAdapter` protocol.
  - Minimal FastAPI application setup in `app/main.py`.

- **Deterministic Validators (Phase 2):**
  - `ConnectivityValidator`: Ensures proper transit legs exist when moving between different cities.
  - `GeographyValidator`: Uses Haversine distance checks to enforce valid walking/transit time and prevent overlapping/teleportation.
  - `OpeningHoursValidator`: Enforces venue opening hours and closed days.
  - `BudgetValidator`: Enforces hard limits on user trip budget.
  - Added 10 JSON fixtures in `tests/fixtures/must_fail/` representing deterministic violation scenarios.
  - Full automated test suite for tool registry idempotency, circuit breakers limits, graph loop termination, and deterministic validators.

- **End-to-End & Security Layer (Phase 4):**
  - Static retrieval adapter implemented, loading fixture data from `data/gtfs`, `data/osm`, and `data/wikivoyage`.
  - Prompt injection defense added via `core/untrusted.py` with structural separation of retrieved untrusted content.
  - Wrote 11 injection attack test fixtures covering varied attack vectors (direct instructions, format spoofing, roleplaying).
  - Human-in-the-loop `ApprovalQueue` integrated directly into the `execute_writes` state machine logic.
  - Backend `FastAPI` server configured to emit `Server-Sent Events` (SSE) displaying real-time streaming of graph progression.
  - Initialized Angular 18 frontend containing a `TimelineComponent` consuming the SSE stream to display the live planning process.

- **Trajectory Evaluation & MCP Server (Phase 5):**
  - Added `mcp` dependency to power local IDE interaction.
  - Added 20 AI-generated Scenario JSON files for evaluation in `evals/scenarios/`.
  - Created `ScenarioSet` registry to parse, version, and load scenarios using strict Pydantic validation.
  - Implemented `evals/trajectory.py` harness to execute `create_planner_graph()` programmatically and compute feasibility, constraint, and injection defense metrics.
  - Configuration settings in `app/settings.py` now support reproducible Git SHA snapshots (via CI environment variable or fallback to local Git metadata).
  - Built TripAgent MCP Server (`mcp_server/server.py`) using `stdio` transport.
  - MCP securely maps `read` tools to MCP tools while intentionally exposing `write` tools only to return a programmatic rejection (forcing writes to the human approval queue).
  - Tested MCP access boundaries successfully (`test_mcp_boundaries.py`).

- **Launch & Analytics (Phase 6):**
  - Executed full trajectory evaluation suite saving runs to `eval_runs/`.
  - Generated automated README metrics tables directly from evaluation data (0 hand-written metrics).
  - Authored `docs/FAILURE-MODES.md` cataloging 6 specific failure root causes and justifications for "won't fix" decisions.
  - Implemented Demo Cache architecture (`scripts/precompute_demo_scenarios.py`) and integrated it into `app/main.py`.
  - Configured `POST /plan` to replay cached SSE events for demo scenarios and fallback to structured JSON rejection for unauthenticated free-form queries.
  - Authored `docs/DEMO-SCENARIOS.md` with 8 curated scenarios showcasing the system's highlights.
  - Configured automated deployments via GitHub Actions (`deploy.yml` and `keepalive.yml`) to Cloudflare Pages (Frontend) and GCP Cloud Run (Backend).

- **Observability & Hardening (Phase 7):**
  - Integrated OpenTelemetry GenAI semantic conventions in `core/telemetry.py` recording spans with latency, purpose, model, and system across planner nodes and SSE streaming.
  - Unified `AuditTrail` into a single Pydantic `BaseModel` supporting indexing, appending, and JSON/markdown export.
  - Implemented `submit_sync` on `ApprovalQueue` enabling synchronous LangGraph execution alongside streaming async APIs.
  - Corrected Cloudflare Pages build directory path in `deploy.yml` from `frontend` to `web`.
  - Added dedicated OpenTelemetry span validation test suite (`tests/test_telemetry.py`).

- **Real LLM Grounding & Trajectory Evaluation (Phase 8):**
  - Designed multi-tier model provider abstraction (`providers/base.py`, `providers/openai_compatible.py`, `providers/factory.py`) adhering to `AGENTS.md` Section 1.3:
    - Low-cost tier routes to **DeepSeek-V4.1-Flash** (API model `deepseek-flash`) for cost-effective offline batch evaluations ($0.14/1M in, $0.28/1M out).
    - Western-hosted tier routes to OpenAI `gpt-4o-mini` for user-facing requests.
  - Replaced rule-based drafting stub with LLM structured generation (`agenerate_structured`), injecting retrieved venues and GTFS transit legs inside `<DATA>...</DATA>` untrusted context tags.
  - Implemented validator critique feedback loop injecting failure explanations into up to 3 replanning rounds.
  - Added unit test suites for LLM drafting and providers (`tests/test_llm_drafting.py`, `tests/test_providers.py`).
  - Executed 20-scenario trajectory evaluation with DeepSeek-V4.1-Flash (`run_deepseek_6babf91_20261020T023119Z.jsonl`):
    - Verified 0.0% hallucination rate across all 20 scenarios using deterministic `FixtureSource` check against raw GTFS and Wikivoyage data.
    - Measured 95.7% constraint satisfaction rate and 55.0% feasibility rate.
    - Verified honest infeasibility detection (10.0%) on impossible requests (e.g. coach exclusion exceeding budget).
    - Recorded average cost per itinerary of $0.0027 (~0.27 cents / run).
  - Upgraded frontend to **Angular 21** (`@angular/core@21.2.25`, `@angular/cli@21.2.27`, `zone.js@0.15.1`, `typescript@5.9.3`) with static build output for Cloudflare Pages.
  - Corrected state key bug in `scripts/precompute_demo_scenarios.py` and regenerated `data/demo_cache.json` with genuine DeepSeek-V4.1-Flash runs for all 8 demo scenarios.
  - Enhanced Angular `TimelineComponent` with rich itinerary cards rendering Day numbers, verified Wikivoyage venue details, GTFS transit routes, time blocks, and ticket costs.

- **Neon DB Presets, Rate Limiting & Gemini 3.5 Flash-Lite (Phase 9):**
  - Seeded all 20 evaluated benchmark scenarios into Neon PostgreSQL (`preset_scenarios` table) with structured metadata, category tags, and full SSE events for instant replay.
  - Built an async repository in `core/db.py` using `asyncpg` with graceful fallback to `data/preset_cache.json` for resilience and zero unexpected compute cost.
  - Implemented 20 interactive preset scenario cards on the Angular landing page with real-time category filtering (`Romantic`, `Transit`, `Budget`, `Accessibility`, `Family`, etc.) and instant SSE replay from database.
  - Enforced a sliding-window in-memory rate limiter in `core/rate_limit.py` restricting custom/new scenarios to 5 calls per 10 minutes per IP (`RATE_LIMIT_CALLS=5`, `RATE_LIMIT_WINDOW_SECONDS=600`) while allowing unlimited preset scenario exploration.
  - Configured default AI model to Google Gemini `gemini-3.5-flash-lite` (`DEFAULT_AI_PROVIDER=gemini`) with an automated `FailoverProvider` to OpenAI `gpt-4o-mini` (with `deepseek-flash` secondary fallback) to ensure 100% service uptime during quota limits.


