import hashlib

from src.rag.loaders.documents import Document
from src.rag.retrieval.bm25_search import BM25Searcher
from src.rag.retrieval.reranker import CrossEncoderReranker
from src.rag.retrieval.vector_search import VectorSearcher
from src.utils.logger import custom_logger as logger


class HybridRetriever:
    """
    Unified Hybrid Search Retriever:
    1. Runs Dense Vector Search (Qdrant) and Sparse Keyword Search (BM25) in parallel.
    2. Merges candidate outputs using Reciprocal Rank Fusion (RRF) with k=60.
    3. Reranks the top merged candidates using BGE Cross-Encoder weights.
    4. Filters out irrelevant documents below threshold.

    Fault-tolerant: if Qdrant is unavailable, gracefully degrades to BM25-only search.
    """
    def __init__(self):
        # VectorSearcher depends on Qdrant — may fail if Qdrant is not running.
        # We catch the error so BM25 + reranker can still operate standalone.
        try:
            self.vector_searcher = VectorSearcher()
        except Exception as e:
            logger.warning(
                f"VectorSearcher unavailable (Qdrant likely not running): {e}. "
                "Falling back to BM25-only retrieval."
            )
            self.vector_searcher = None

        self.bm25_searcher = BM25Searcher()
        self.reranker = CrossEncoderReranker()

    def _get_doc_key(self, doc: Document) -> str:
        """
        Generates a unique lookup key for a document based on its text content.
        Helps de-duplicate records across dense and sparse searches.
        """
        meta = doc.metadata or {}
        # Try chunk_id or id first, fallback to SHA256 content hash
        doc_id = meta.get("chunk_id") or meta.get("id")
        if doc_id:
            return str(doc_id)
        
        # Fallback to text hashing
        return hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()

    def rrf_merge(self, dense_docs: list[Document], sparse_docs: list[Document], k: int = 60) -> list[Document]:
        """
        Merges dense and sparse lists using Reciprocal Rank Fusion (RRF) algorithm.
        RRF Score: sum( 1 / (k + rank) ) for each search source.
        """
        rrf_scores = {}
        doc_map = {}

        # 1. Score dense candidates
        for rank, doc in enumerate(dense_docs):
            key = self._get_doc_key(doc)
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k + rank))

        # 2. Score sparse candidates
        for rank, doc in enumerate(sparse_docs):
            key = self._get_doc_key(doc)
            # If document is not in doc_map, add it
            if key not in doc_map:
                doc_map[key] = doc
            # Accumulate rank score
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k + rank))

        # 3. Sort keys by accumulated RRF score descending
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 4. Compile merged list with scores
        merged_docs = []
        for key in sorted_keys:
            doc = doc_map[key]
            # Update metadata
            doc.metadata.update({
                "rrf_score": rrf_scores[key],
                "score": rrf_scores[key]
            })
            merged_docs.append(doc)

        return merged_docs

    async def retrieve(
        self,
        query: str,
        limit: int = 3,
        category: str | None = None,
        department: str | None = None,
        doc_type: str | None = None,
        candidate_multiplier: int = 4
    ) -> list[Document]:
        """
        Orchestrates dense search, sparse search, RRF fusion, and Cross-Encoder reranking.
        Safe execution boundary: handles all component errors gracefully.
        """
        if not query.strip():
            return []

        # We pull a larger set of candidates for RRF and reranking
        candidates_limit = limit * candidate_multiplier
        
        try:
            # Step 1: Run Dense Vector Search (skip gracefully if Qdrant is down)
            if self.vector_searcher is not None:
                dense_results = await self.vector_searcher.search_all(
                    query=query,
                    limit=candidates_limit,
                    category=category,
                    department=department,
                    doc_type=doc_type
                )
            else:
                dense_results = []
                logger.debug("Dense search skipped — VectorSearcher not available.")

            # Step 2: Run Sparse BM25 Search
            sparse_results = self.bm25_searcher.search(
                query=query,
                limit=candidates_limit,
                category=category,
                department=department,
                doc_type=doc_type
            )

            logger.info(f"Retrieved candidates: Dense={len(dense_results)}, Sparse={len(sparse_results)}")

            # Step 3: Reciprocal Rank Fusion (RRF)
            fused_docs = self.rrf_merge(dense_results, sparse_results, k=60)
            logger.info(f"RRF Fusion completed: {len(fused_docs)} unique merged candidates.")

            if not fused_docs:
                return []

            # Step 4: Cross-Encoder Reranking
            # Pass top fused candidates to Reranker for exact scoring
            top_fused_candidates = fused_docs[:limit * 3]
            reranked_docs = await self.reranker.rerank(
                query=query,
                candidates=top_fused_candidates,
                limit=limit
            )

            return reranked_docs

        except Exception as e:
            logger.error(f"Failed to execute hybrid search query '{query}': {e}")
            # Fault-tolerant fallback: return empty list on failure instead of crashing the loop
            return []
