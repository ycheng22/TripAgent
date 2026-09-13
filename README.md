# TripAgent

TripAgent is a production-grade AI travel planning system that orchestrates deterministic validators, human-in-the-loop approvals, and strict prompt injection defenses over actual geographic transit data.

![Architecture Diagram](TODO_INSERT_ARCHITECTURE_DIAGRAM_HERE)

## Metrics & Conventions

**Conventions**: 
- Gain mapping: Exact=3, Substitute=2, Complement=1, Irrelevant=0.
- "Relevant" means gain > 0.
- Empty qrels queries are skipped.
- Metric values shown are strictly measured from `eval_runs\run_a2e0d4f_20260910T031129Z.jsonl` (a2e0d4f977c92aa5b063bbfb6f7d0ad898e872b1).

| Metric | Score |
| --- | --- |
| Feasibility Rate | 55.0% |
| Constraint Satisfaction | 100.0% |
| Hallucination Rate | 0.0% |
| Honest Infeasibility | 0.0% |
| False Feasible | 45.0% |
| Injection Block Rate | TBD |
| Mean Steps | TBD |
| p95 Steps | TBD |
| Cost per Task | TBD |

### Breakdown by Category
| Category | Total | Feasible % | Hallucination % |
|---|---|---|---|
| Tight Budget | 1 | 100.0% | 0.0% |
| Deliberately Infeasible | 9 | 100.0% | 0.0% |
| Single-City | 5 | 100.0% | 0.0% |
| Multi-City | 3 | 100.0% | 0.0% |
| Strong Preference | 2 | 100.0% | 0.0% |

## Security & Audit Trail

Every interaction is tracked for reproducibility and cost attribution. All writes are safely gated behind the Model Context Protocol (MCP) and require human approval.

### Example Audit Record
| step | action_type | tool_name | duration_ms | tokens_in | tokens_out | cost_usd |
|---|---|---|---|---|---|---|
| 0 | LLM Call | None | 2150 | 1850 | 350 | 0.005 |
| 1 | Validation | GeographyValidator | 15 | 0 | 0 | 0.000 |
| 2 | Replan | None | 1820 | 2250 | 410 | 0.007 |

## Five-Layer Architecture

1. **App Layer**: FastAPI server orchestrating the state machine, streaming real-time Server-Sent Events (SSE) to the Angular frontend.
2. **Core Layer**: LangGraph logic engine (`parse_constraints` -> `retrieve` -> `draft_itinerary` -> `validate` -> `replan`).
3. **Validation Layer**: Deterministic rules engines (`GeographyValidator`, `BudgetValidator`, `ConnectivityValidator`) ensuring physically impossible plans fail fast.
4. **Adapter Layer**: Static retrieval engines mapping real-world data (`gtfs`, `osm`, `wikivoyage`) to the planner context.
5. **Security Layer**: `core/untrusted.py` and MCP server explicitly decoupling generated structure from uncontrolled inputs.

## Known Limitations

- **Geographic Data**: GTFS data currently strictly covers exactly 5 cities.
- **Cross-border Transit**: Cross-border surface class transit schedules are not integrated yet.
- **Accommodation Constraints**: "Stay" logic does not verify hotel capacity/live pricing, it operates strictly on cached median pricing per venue.
- TODO: Human to add further narrative limitations.