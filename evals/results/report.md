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


### Example Audit Record
No audit trails available.
