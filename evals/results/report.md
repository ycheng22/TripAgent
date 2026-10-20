## Metrics & Conventions

**Conventions**: 
- Gain mapping: Exact=3, Substitute=2, Complement=1, Irrelevant=0.
- "Relevant" means gain > 0.
- Empty qrels queries are skipped.
- Provider / Model: DeepSeek-V4.1-Flash (`deepseek-flash`) via `low_cost` tier.
- Metric values shown are strictly measured from `eval_runs\run_deepseek_6babf91_20261020T023119Z.jsonl` (6babf91803bcea2d66078b80a53c03933daffcfc).

| Metric | Score |
| --- | --- |
| Feasibility Rate | 55.0% |
| Constraint Satisfaction | 95.7% |
| Hallucination Rate | 0.0% |
| Honest Infeasibility | 10.0% |
| False Feasible | 35.0% |
| Injection Block Rate | N/A |
| Mean Steps | 2.3 |
| p95 Steps | 7 |
| Cost per Task | $0.0027 |

### Breakdown by Category
| Category | Total | Feasible % | Hallucination % |
|---|---|---|---|
| Tight Budget | 1 | 100.0% | 0.0% |
| Deliberately Infeasible | 9 | 77.8% | 0.0% |
| Single-City | 5 | 100.0% | 0.0% |
| Multi-City | 3 | 100.0% | 0.0% |
| Strong Preference | 2 | 100.0% | 0.0% |


### Example Audit Record
| step_index | action_type | tool_name | source_id | source_version | duration_ms | tokens_in | tokens_out | cost_usd | validator_failures | timestamp |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | draft_itinerary | agenerate_structured | deepseek | deepseek-flash | 13511 | 3452 | 2819 | 0.0013 | 0 | 2026-10-20T02:21:09.214455+00:00 |
