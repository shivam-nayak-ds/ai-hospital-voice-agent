from src.rag.retrieval.hybrid_search import HybridRetriever

# Standardized singleton instance provider for RAG Specialist Agent
_retriever_instance = None

def get_retriever() -> HybridRetriever:
    """
    Singleton retriever provider. Ensures model and DB connections
    are initialized once and shared across agent sessions.
    """
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance
