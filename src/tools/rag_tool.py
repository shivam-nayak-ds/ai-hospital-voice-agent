"""
rag_tool.py
-----------
Production-grade RAG Tool: retrieve_hospital_info.
Implements complete RAG lifecycle:
  1. Spoken Query Understanding & Rewriting (QueryUnderstandingEngine)
  2. Dense Vector Search (Qdrant) + Sparse Keyword Search (BM25)
  3. Reciprocal Rank Fusion (RRF k=60)
  4. BGE Cross-Encoder Reranker
  5. Safety Guardrails & Citation Formatting
"""

from typing import Optional, List
from src.rag.retrieval.retriever import get_retriever
from src.rag.processing.query_rewriter import QueryUnderstandingEngine
from src.utils.logger import custom_logger as logger


async def retrieve_hospital_info(query: str, limit: int = 3) -> str:
    """
    Production entry point for the Hospital Knowledge Retrieval Layer.
    Executes the entire RAG pipeline from query rewriting to reranked contextual chunks.
    """
    if not query or len(query.strip()) < 2:
        return "Please provide a valid question to search hospital information."

    try:
        # Step 1: Query Understanding, Rewriting & Metadata Filter Extraction
        rewritten_query, dept_filter, cat_filter = QueryUnderstandingEngine.process_query(query)

        # Step 2: Retrieve from Hybrid Retriever (Qdrant Dense + BM25 Sparse + RRF + Reranker)
        retriever = get_retriever()
        docs = await retriever.retrieve(
            query=rewritten_query,
            limit=limit,
            department=dept_filter,
            category=cat_filter
        )

        # Step 2b: Fallback to broader search if strict filter returned nothing
        if not docs and (dept_filter or cat_filter):
            logger.info("Filtered RAG search returned 0 items; falling back to un-filtered hybrid search.")
            docs = await retriever.retrieve(query=rewritten_query, limit=limit)

        if not docs:
            logger.info(f"RAG Tool: No information found for query: '{query}' (rewritten: '{rewritten_query}')")
            return "No relevant hospital policies or information found."

        # Step 3: Context Formatting with Citations & Metadata
        context_parts: List[str] = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Lifeline Knowledge Base")
            dept = doc.metadata.get("department", "General")
            category = doc.metadata.get("category", "General")
            score = doc.metadata.get("score", doc.metadata.get("rerank_score", 0.0))

            header = f"[Source {i}: {source} | Dept: {dept} | Cat: {category} | Relevancy: {score:.2f}]"
            content = doc.page_content.strip()
            context_parts.append(f"{header}\n{content}")

        logger.success(f"RAG Tool: Retrieved and reranked {len(docs)} high-confidence chunks for '{query}'")
        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.error(f"RAG Tool runtime error for query '{query}': {e}")
        return "Error: Hospital information lookup temporarily unavailable."
