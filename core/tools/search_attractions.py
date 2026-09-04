from pydantic import BaseModel
from typing import Literal
from core.models import Venue, Coordinate
from adapters.wikivoyage import WikivoyageAdapter
from adapters.static_retriever import StaticRetriever
from retrieval_core.models import Query
import asyncio

class SearchAttractionsArgs(BaseModel):
    city: str
    query: str
    top_k: int = 5

class SearchAttractionsTool:
    name: str = "search_attractions"
    description: str = "Search for attractions/venues in a specific city."
    args_model = SearchAttractionsArgs
    access: Literal["read"] = "read"

    def execute(self, args: SearchAttractionsArgs) -> list[Venue]:
        retriever = StaticRetriever()
        adapter = WikivoyageAdapter()
        
        # We need an event loop since retrieval is async
        loop = asyncio.new_event_loop()
        try:
            hits = loop.run_until_complete(retriever.retrieve(Query(text=f"{args.city} {args.query}"), args.top_k))
            venues = []
            if hits:
                docs = loop.run_until_complete(adapter.mget_documents([h.doc_id for h in hits if h.doc_id]))
                for doc in docs:
                    venues.append(Venue(
                        venue_id=doc.doc_id,
                        name=doc.metadata["name"],
                        city=doc.metadata["city"],
                        coord=Coordinate(lat=doc.metadata["lat"], lon=doc.metadata["lon"]),
                        source_id=doc.metadata["source_id"],
                        source_version=doc.metadata["source_version"]
                    ))
            return venues
        finally:
            loop.close()
