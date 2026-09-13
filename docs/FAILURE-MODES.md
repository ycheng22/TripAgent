# Failure Modes

This document catalogues the known failure modes of TripAgent. It is not a list of raw error logs, but a taxonomy of root causes. For each failure mode, we specify its symptom, root cause, impact, current mitigation, and why certain modes are intentionally left unaddressed (won't fix).

## 1. Schema Drift (Hallucinated Pydantic Fields)
- **Symptom**: The LLM output parses as valid JSON but fails Pydantic validation because it invents fields or nests them incorrectly.
- **Root Cause**: Base LLMs (especially smaller models) lack strict adherence to complex OpenAPI schemas without constrained decoding.
- **Impact**: High. Causes the planner to abort the current replan loop.
- **Current Mitigation**: We use `Instructor` / native structured outputs where possible, and enforce strict Pydantic models. We retry up to 3 times on schema errors.
- **Won't Fix**: We do not implement heuristic JSON repair (like regex patching) because it masks underlying prompt weaknesses and leads to unpredictable downstream failures.

## 2. Geographic Teleportation (Spatial Infeasibility)
- **Symptom**: The planner schedules a morning coffee in Paris and an afternoon museum visit in Berlin, with no transit step between them.
- **Root Cause**: The LLM lacks intrinsic spatial reasoning. It optimizes for semantic flow ("coffee then museum") rather than geographic reality.
- **Impact**: Critical. This makes the itinerary physically impossible.
- **Current Mitigation**: The `GeographyValidator` calculates Haversine distance and enforces a minimum transit time. If violated, it returns a hard `infeasible` violation, forcing a replan.
- **Won't Fix**: We do not inject a full routing engine (OSRM/Google Maps) into the LLM prompt. Providing the LLM with point-to-point times for every combination explodes the context window.

## 3. Temporal Paradox (Opening Hours Violation)
- **Symptom**: Planning a visit to the Louvre on a Tuesday, or scheduling a 4-hour museum visit between 16:00 and 20:00 when the museum closes at 18:00.
- **Root Cause**: The LLM relies on its parametric memory for general facts (which may be wrong) and ignores retrieved metadata if it contradicts its priors.
- **Impact**: High. Ruins the user's real-world experience.
- **Current Mitigation**: The `OpeningHoursValidator` cross-references the proposed `starts_at` and `ends_at` against the retrieved `Venue` metadata.
- **Won't Fix**: We do not attempt to "slide" the schedule automatically in code. The LLM must explicitly rewrite the schedule so the rest of the day adjusts organically.

## 4. Hallucinated Transit Legs
- **Symptom**: The LLM invents a convenient "Bullet Train" from Amsterdam to Prague that takes 2 hours.
- **Root Cause**: The LLM fabricates data to satisfy user constraints when retrieved GTFS data is sparse or inconvenient.
- **Impact**: Critical. Safety and trust failure.
- **Current Mitigation**: The `ConnectivityValidator` strictly checks the `trip_id` against the loaded GTFS fixture. If it does not exist, the plan is rejected.
- **Won't Fix**: We do not support cross-border flight inference (e.g. "Just fly there"). The scope is strictly limited to GTFS surface transit to maintain deterministic verification.

## 5. False Feasible (Systemic Over-optimism)
- **Symptom**: The user requests 10 cities in 2 days. The LLM successfully produces a plan, but only visits 2 cities, silently dropping the other 8 to pass validators.
- **Root Cause**: The LLM is optimizing for validator approval rather than constraint satisfaction, leading to a "stealth relaxation" of user constraints.
- **Impact**: Medium. The plan is physically possible, but the user's request was ignored.
- **Current Mitigation**: We track `constraint_satisfaction_rate` separately from `feasibility_rate` to detect this.
- **Won't Fix**: We do not write a deterministic "Did it visit all cities?" validator because natural language requests are often ambiguous ("Try to fit in Paris if possible"). We rely on honest infeasibility prompts instead.

## 6. Prompt Injection False Positives
- **Symptom**: A legitimate request like "Plan a trip to the Spy Museum and act out a secret agent scenario" gets flagged as an injection attack.
- **Root Cause**: The safety boundary (heuristics and structural checks) is overly sensitive to imperative verbs or roleplay keywords.
- **Impact**: Low/Medium. Frustrates users but fails safe.
- **Current Mitigation**: Structural separation of untrusted data in `core/untrusted.py`.
- **Won't Fix**: We will not weaken the injection defense to accommodate edge-case roleplay. In a production system executing write tools (bookings/payments), a false positive is infinitely preferable to a false negative.
