"""
rag_tool.py
-----------
Tool: retrieve_hospital_info
Calls the Hybrid RAG pipeline (Qdrant dense search + BM25 + BGE Reranker)
to fetch relevant hospital policies, FAQs, and department information.
"""

from src.rag.retrieval.retriever import get_retriever
from src.utils.logger import custom_logger as logger

async def retrieve_hospital_info(query: str, limit: int = 3) -> str:
    if not query or len(query.strip()) < 3:
        return "Please provide a valid question to search hospital information."

    try:
        retriever = get_retriever()
        docs = await retriever.retrieve(query=query, limit=limit)

        if not docs:
            logger.info(f"RAG Tool: No information found for '{query}'")
            return "No relevant hospital policies or information found."

        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Hospital Knowledge Base")
            context_parts.append(f"[Source {i}: {source}]\n{doc.page_content.strip()}")

        logger.info(f"RAG Tool: Retrieved {len(docs)} chunks for: '{query}'")
        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.error(f"RAG Tool error: {e}")
        return "Error: Hospital information lookup unavailable."
