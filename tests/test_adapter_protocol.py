from adapters.wikivoyage import WikivoyageAdapter
from retrieval_core.adapters.base import DocumentAdapter
from typing import get_type_hints, Any

def test_adapter_protocol():
    adapter = WikivoyageAdapter()
    
    # Check that it has the required methods
    assert hasattr(adapter, "get_document")
    assert hasattr(adapter, "mget_documents")
    
    # We can also check structurally by trying to instantiate it as if we were passing it to something expecting a DocumentAdapter
    def consume_adapter(a: DocumentAdapter) -> None:
        pass
        
    consume_adapter(adapter) # type-check passes structurally
