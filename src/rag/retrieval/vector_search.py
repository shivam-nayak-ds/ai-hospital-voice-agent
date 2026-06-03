from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.rag.embeddings.embedding_model import EmbeddingModel
from src.rag.vectordb.qdrant_client import get_qdrant_client
from src.rag.loaders.documents import Document
from src.rag.config.settings import rag_settings
from src.utils.logger import custom_logger as logger

class VectorSearcher:
    """
    Production-ready Dense Vector Searcher querying Qdrant collections
    with dynamic payload pre-filtering and similarity threshold checking.
    """
    def __init__(self):
        try:
            self.client = get_qdrant_client()
            self.embedder = EmbeddingModel()
        except Exception as e:
            logger.critical(f"VectorSearcher initialization failed: {e}")
            raise e

    def _build_filter(
        self, 
        category: Optional[str] = None, 
        department: Optional[str] = None, 
        doc_type: Optional[str] = None
    ) -> Optional[models.Filter]:
        """
        Translates raw parameters into Qdrant keyword query payload filters.
        """
        conditions = []

        if category:
            conditions.append(
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category.strip())
                )
            )

        if department:
            conditions.append(
                models.FieldCondition(
                    key="department",
                    match=models.MatchValue(value=department.strip().lower())
                )
            )

        if doc_type:
            conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=doc_type.strip())
                )
            )

        if not conditions:
            return None

        return models.Filter(must=conditions)

    def search_collection(
        self,
        query: str,
        collection_name: str,
        limit: int = 5,
        category: Optional[str] = None,
        department: Optional[str] = None,
        doc_type: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Queries a single Qdrant collection with dynamic filtering and score thresholding.
        Safe execution boundary: catches all exceptions and logs them without throwing.
        """
        if not query.strip():
            return []

        search_threshold = threshold if threshold is not None else rag_settings.SIMILARITY_THRESHOLD
        
        try:
            # 1. BGE query instruction prepending for retrieval enhancement
            query_prefix = "Represent this query for retrieving relevant documents: "
            formatted_query = f"{query_prefix}{query.strip()}"

            # 2. Embed Query
            query_vector = self.embedder.embed_text(formatted_query)
            if not query_vector:
                logger.error(f"Failed to generate embedding for query: '{query}'")
                return []

            # 3. Build Filters
            qdrant_filter = self._build_filter(category, department, doc_type)

            # 4. Execute Search via query_points API (Standard in qdrant-client v1.10+)
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True
            )
            hits = response.points

            # 5. Parse and Filter by Similarity Score Threshold
            results: List[Document] = []
            for hit in hits:
                if hit.score >= search_threshold:
                    payload = hit.payload or {}
                    page_content = payload.pop("page_content", "")
                    
                    # Inject score and collection origin in metadata
                    metadata = payload.copy()
                    metadata.update({
                        "score": hit.score,
                        "collection": collection_name,
                        "search_type": "dense"
                    })
                    
                    results.append(Document(page_content=page_content, metadata=metadata))
            
            logger.debug(f"Dense vector search returned {len(results)}/{len(hits)} hits above {search_threshold} in '{collection_name}'")
            return results

        except Exception as e:
            logger.error(f"Error during vector search in collection '{collection_name}': {e}")
            # Fault-tolerant response: return empty list instead of crashing the process
            return []

    def search_all(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
        department: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> List[Document]:
        """
        Searches both FAQ and Markdown collections and merges results sorted by similarity score.
        """
        results = []
        
        # Search FAQs if doc_type is FAQ or not specified
        if not doc_type or doc_type == "faq":
            faq_results = self.search_collection(
                query=query,
                collection_name=rag_settings.FAQ_COLLECTION,
                limit=limit,
                category=category,
                department=department,
                doc_type="faq"
            )
            results.extend(faq_results)

        # Search Markdown Policies if doc_type is policy/guidelines or not specified
        if not doc_type or doc_type != "faq":
            md_results = self.search_collection(
                query=query,
                collection_name=rag_settings.MARKDOWN_COLLECTION,
                limit=limit,
                category=category,
                department=department,
                doc_type=doc_type
            )
            results.extend(md_results)

        # Sort combined results by similarity score descending
        results.sort(key=lambda d: d.metadata.get("score", 0.0), reverse=True)
        return results[:limit]
