import json
from pathlib import Path

from retrieval_core.models import Document  # type: ignore[import-untyped]


class WikivoyageAdapter:
    def __init__(self, data_dir: Path = Path("data/wikivoyage")):
        self.data_dir = data_dir
        self.venues = {}
        if self.data_dir.exists():
            for file_path in self.data_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    for venue in data:
                        self.venues[venue["venue_id"]] = venue
                except (json.JSONDecodeError, OSError):
                    continue

    async def get_document(self, doc_id: str) -> Document | None:
        if doc_id in self.venues:
            v = self.venues[doc_id]
            return Document(
                doc_id=doc_id,
                metadata={
                    "name": v["name"],
                    "city": v["city"],
                    "lat": v["coord"]["lat"],
                    "lon": v["coord"]["lon"],
                    "source_id": v["source_id"],
                    "source_version": v["source_version"],
                    "description": v["description"],
                    "opening_hours": v["opening_hours"],
                    "prices": v["prices"]
                }
            )
        return None

    async def mget_documents(self, doc_ids: list[str]) -> list[Document]:
        docs = []
        for did in doc_ids:
            doc = await self.get_document(did)
            if doc:
                docs.append(doc)
        return docs
