import json
import math
from pathlib import Path
from typing import Any
from retrieval_core.models import Query, ScoredHit, ScoreBreakdown

class StaticRetriever:
    def __init__(self, data_dir: Path = Path("data/wikivoyage")):
        self.data_dir = data_dir
        self.documents = []
        if self.data_dir.exists():
            for file_path in self.data_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    self.documents.extend(data)
                except Exception:
                    pass

    async def retrieve(self, query: Query, top_k: int) -> list[ScoredHit]:
        # Simple keyword matching for the temporary substitute
        query_terms = set(query.text.lower().split())
        hits = []
        
        for doc in self.documents:
            text_to_search = f"{doc.get('name', '')} {doc.get('city', '')} {doc.get('description', '')}".lower()
            matched_terms = [t for t in query_terms if t in text_to_search]
            
            if matched_terms:
                # Give a simple score based on match count
                score = float(len(matched_terms))
                hits.append(ScoredHit(
                    doc_id=doc["venue_id"],
                    raw_score=score,
                    retriever_name="static_json",
                    rank=0, # will set after sort
                    breakdown=ScoreBreakdown(bm25_score=score, matched_terms=matched_terms)
                ))
                
        # Sort by score descending
        hits.sort(key=lambda x: x.raw_score, reverse=True)
        
        # Limit and set rank
        result = hits[:top_k]
        for i, hit in enumerate(result):
            hit.rank = i + 1
            
        return result
