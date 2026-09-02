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
