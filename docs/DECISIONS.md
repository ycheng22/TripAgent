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
