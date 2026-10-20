import json
import re
from pathlib import Path
from typing import Any

from retrieval_core.models import (  # type: ignore[import-untyped]
    Query,
    ScoreBreakdown,
    ScoredHit,
)


class StaticRetriever:
    def __init__(self, data_dir: Path = Path("data/wikivoyage")):
        self.data_dir = data_dir
        self.documents: list[dict[str, Any]] = []
        if self.data_dir.exists():
            for file_path in self.data_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    self.documents.extend(data)
                except (json.JSONDecodeError, OSError):
                    continue

    async def retrieve(self, query: Query, top_k: int) -> list[ScoredHit]:
        # Extract alphanumeric query terms
        query_terms = set(re.findall(r"\b[a-zA-Z0-9_\-]+\b", query.text.lower()))
        hits = []

        for doc in self.documents:
            city = doc.get("city", "").lower()
            name = doc.get("name", "").lower()
            desc = doc.get("description", "").lower()

            matched_terms = [t for t in query_terms if t in name or t in city or t in desc]

            if matched_terms:
                score = 0.0
                for t in matched_terms:
                    if t in city:
                        score += 3.0
                    elif t in name:
                        score += 2.0
                    else:
                        score += 1.0
                hits.append(ScoredHit(
                    doc_id=doc["venue_id"],
                    raw_score=score,
                    retriever_name="static_json",
                    rank=0,
                    breakdown=ScoreBreakdown(bm25_score=score, matched_terms=matched_terms)
                ))

        # Sort by score descending
        hits.sort(key=lambda x: x.raw_score, reverse=True)

        # Fallback to include remaining documents if fewer than top_k
        if len(hits) < top_k:
            existing_ids = {h.doc_id for h in hits}
            for doc in self.documents:
                if doc["venue_id"] not in existing_ids:
                    hits.append(ScoredHit(
                        doc_id=doc["venue_id"],
                        raw_score=0.1,
                        retriever_name="static_json",
                        rank=0,
                        breakdown=ScoreBreakdown(bm25_score=0.1, matched_terms=[])
                    ))
                    existing_ids.add(doc["venue_id"])
                    if len(hits) >= top_k:
                        break

        result = hits[:top_k]
        for i, hit in enumerate(result):
            hit.rank = i + 1

        return result
