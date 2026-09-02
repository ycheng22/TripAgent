from retrieval_core.models import Document

class WikivoyageAdapter:
    async def get_document(self, doc_id: str) -> Document | None:
        # Stub
        if "stub" in doc_id:
            return Document(
                doc_id=doc_id,
                metadata={
                    "name": "Stub Venue",
                    "city": "Berlin",
                    "lat": 52.52,
                    "lon": 13.40,
                    "source_id": "wikivoyage",
                    "source_version": "2024-01-stub"
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
