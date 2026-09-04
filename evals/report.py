import os
from datetime import datetime

def generate_report(results: list, source, output_dir: str = "evals/results"):
    os.makedirs(output_dir, exist_ok=True)
    
    total = len(results)
    feasible_count = sum(1 for r in results if r["state"].get("status") == "finalised")
    
    # Just basic reporting for now
    report = f"""# Trajectory Evaluation Report
Date: {datetime.now().isoformat()}

## Summary
- **Total Scenarios Evaluated**: {total}
- **Feasible Itineraries Generated**: {feasible_count}
- **Feasibility Rate**: {feasible_count / total if total > 0 else 0:.2%}

## Details
"""
    for r in results:
        scenario = r["scenario"]
        state = r["state"]
        status = state.get("status")
        report += f"- {scenario._filename}: {status}\n"
        
    with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Report generated at {output_dir}/report.md")

if __name__ == "__main__":
    pass
