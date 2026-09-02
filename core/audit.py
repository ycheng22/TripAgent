import json
from pathlib import Path
from core.models import AuditRecord

class AuditTrail:
    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self.records.append(record)

    def to_markdown(self) -> str:
        if not self.records:
            return "No audit records."
        
        headers = [
            "step_index", "action_type", "tool_name", "source_id", "source_version", 
            "duration_ms", "tokens_in", "tokens_out", "cost_usd", "validator_failures", "timestamp"
        ]
        
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        
        for r in self.records:
            row = [
                str(r.step_index),
                r.action_type,
                str(r.tool_name or ""),
                str(r.source_id or ""),
                str(r.source_version or ""),
                str(r.duration_ms),
                str(r.tokens_in),
                str(r.tokens_out),
                f"{r.cost_usd:.4f}",
                str(r.validator_failures),
                r.timestamp.isoformat()
            ]
            lines.append("| " + " | ".join(row) + " |")
            
        return "\n".join(lines)

    def to_json(self, run_id: str, base_dir: Path) -> Path:
        base_dir.mkdir(parents=True, exist_ok=True)
        out_path = base_dir / f"{run_id}.json"
        data = [json.loads(r.model_dump_json()) for r in self.records]
        out_path.write_text(json.dumps(data, indent=2))
        return out_path
