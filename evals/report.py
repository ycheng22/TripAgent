import os
import json
import glob
from datetime import datetime

from core.models import AuditTrail

def get_category(scenario):
    if scenario.get("expected_feasibility") == "infeasible":
        return "deliberately infeasible"
    req_text = scenario.get("request_text", "").lower()
    cities = ["paris", "berlin", "prague", "amsterdam", "vienna"]
    city_count = sum(1 for c in cities if c in req_text)
    if city_count > 1:
        return "multi-city"
    if scenario.get("constraints", {}).get("excluded_modes"):
        return "strong preference"
    if scenario.get("constraints", {}).get("budget_eur", 1000) < 400:
        return "tight budget"
    return "single-city"

def generate_report(output_dir: str = "evals/results"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Find latest run
    runs = glob.glob("eval_runs/*.jsonl")
    if not runs:
        print("No eval runs found.")
        return
        
    latest_run = max(runs, key=os.path.getctime)
    with open(latest_run, "r", encoding="utf-8") as f:
        run_data = json.loads(f.read().strip())
        
    metrics = run_data["metrics"]
    results = run_data["results"]
    
    # Generate breakdown
    breakdown = {}
    for r in results:
        cat = get_category(r["scenario"])
        if cat not in breakdown:
            breakdown[cat] = {"total": 0, "feasible": 0, "hallucinated": 0}
        breakdown[cat]["total"] += 1
        if r["state"].get("status") == "finalised":
            breakdown[cat]["feasible"] += 1
        if r["hallucinated"]:
            breakdown[cat]["hallucinated"] += 1
            
    breakdown_md = "### Breakdown by Category\n| Category | Total | Feasible % | Hallucination % |\n|---|---|---|---|\n"
    for cat, data in breakdown.items():
        feas_rate = f"{data['feasible']/data['total']:.1%}" if data['total'] else "0.0%"
        hall_rate = f"{data['hallucinated']/data['total']:.1%}" if data['total'] else "0.0%"
        breakdown_md += f"| {cat.title()} | {data['total']} | {feas_rate} | {hall_rate} |\n"
        
    # Get ONE audit trail table
    audit_table = "No audit trails available."
    for r in results:
        if "audit_trail" in r["state"] and r["state"]["audit_trail"]:
            audit_dict = r["state"]["audit_trail"]
            if isinstance(audit_dict, dict) and "records" in audit_dict:
                audit = AuditTrail(**audit_dict)
                audit_table = audit.to_markdown()
                break
                
    # Generate README table
    fmt = lambda x: f"{x:.1%}" if isinstance(x, float) and "rate" in str(x).lower() else x
    
    readme_table = f"""## Metrics & Conventions

**Conventions**: 
- Gain mapping: Exact=3, Substitute=2, Complement=1, Irrelevant=0.
- "Relevant" means gain > 0.
- Empty qrels queries are skipped.
- Metric values shown are strictly measured from `{latest_run}` ({run_data['git_sha']}).

| Metric | Score |
| --- | --- |
| Feasibility Rate | {metrics.get('feasibility_rate', 0):.1%} |
| Constraint Satisfaction | {metrics.get('constraint_satisfaction_rate', 0):.1%} |
| Hallucination Rate | {metrics.get('hallucination_rate', 0):.1%} |
| Honest Infeasibility | {metrics.get('honest_infeasibility_rate', 0):.1%} |
| False Feasible | {metrics.get('false_feasible_rate', 0):.1%} |
| Injection Block Rate | {metrics.get('injection_block_rate', 'TBD')} |
| Mean Steps | {metrics.get('mean_steps', 'TBD')} |
| p95 Steps | {metrics.get('p95_steps', 'TBD')} |
| Cost per Task | {metrics.get('cost_per_task', 'TBD')} |

{breakdown_md}

### Example Audit Record
{audit_table}
"""

    with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(readme_table)
        
    # Generate worst_runs.md (bottom 15 based on hallucination or false feasible)
    worst = [r for r in results if r["hallucinated"] or r["state"].get("status") == "infeasible"]
    # If not enough, just take them all up to 15
    if len(worst) < 15:
        worst = results[:15]
    else:
        worst = worst[:15]
        
    worst_md = "# Worst Runs\n\n"
    for r in worst:
        worst_md += f"### {r['filename']}\n"
        worst_md += f"**Status**: {r['state'].get('status')}\n"
        worst_md += f"**Hallucinated**: {r['hallucinated']}\n"
        worst_md += f"**Violations**: {json.dumps(r['state'].get('violations', []), indent=2)}\n\n"
        
    with open(os.path.join(output_dir, "worst_runs.md"), "w", encoding="utf-8") as f:
        f.write(worst_md)
        
    print(f"Report generated at {output_dir}/report.md and worst_runs.md")

if __name__ == "__main__":
    generate_report()
