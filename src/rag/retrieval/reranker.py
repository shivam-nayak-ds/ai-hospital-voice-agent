from typing import List
from sentence_transformers import CrossEncoder

from src.rag.loaders.documents import Document
from src.rag.config.settings import rag_settings
from src.utils.logger import custom_logger as logger

class CrossEncoderReranker:
    """
    Reranks candidate documents using local BGE Cross-Encoder weights.
    Applies strict threshold filtering and features crash-resilient fallback systems.
    """
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """
        Loads the cross encoder model on CPU/GPU.
        """
        logger.info(f"Loading local Cross-Encoder reranker: {self.model_name}...")
        try:
            self.model = CrossEncoder(self.model_name)
            logger.success(f"Successfully loaded Cross-Encoder model: {self.model_name}")
        except Exception as e:
            logger.critical(f"Failed to load Cross-Encoder {self.model_name}: {e}. Reranking will default to raw scores.")
            self.model = None

    def rerank(
        self,
        query: str,
        candidates: List[Document],
        limit: int = 3,
        threshold: float = None
    ) -> List[Document]:
        """
        Reranks candidates and filters out low relevance scores.
        Safe execution boundary: falls back to raw ranking if model is unreachable.
        """
        if not candidates:
            return []
        
        if not query.strip():
            return candidates[:limit]

        rerank_threshold = threshold if threshold is not None else rag_settings.RERANK_THRESHOLD

        # If model failed to load, fallback to incoming order
        if self.model is None:
            logger.warning("Reranker is inactive. Returning top candidates in raw order.")
            return candidates[:limit]

        try:
            # 1. Format inputs for Cross-Encoder
            pairs = [[query.strip(), doc.page_content] for doc in candidates]
            
            # 2. Predict relevance scores (returns float array)
            scores = self.model.predict(pairs)

            # 3. Enrich candidates with rerank scores
            reranked_docs = []
            for doc, score_val in zip(candidates, scores):
                score = float(score_val)
                # Keep only items meeting the threshold boundary
                if score >= rerank_threshold:
                    doc_copy = Document(page_content=doc.page_content, metadata=doc.metadata.copy())
                    doc_copy.metadata.update({
                        "rerank_score": score,
                        "old_score": doc.metadata.get("score")
                    })
                    # Override principal score for sorting compatibility
                    doc_copy.metadata["score"] = score
                    reranked_docs.append(doc_copy)

            # 4. Sort in descending order of rerank score
            reranked_docs.sort(key=lambda d: d.metadata.get("rerank_score", 0.0), reverse=True)
            logger.info(f"Reranker: Filtered down candidates to {len(reranked_docs)} / {len(candidates)} items above threshold {rerank_threshold}")
            
            return reranked_docs[:limit]

        except Exception as e:
            logger.error(f"Error during Cross-Encoder reranking: {e}. Falling back to input candidates.")
            # Fault-tolerant fallback: return top candidates in raw order
            return candidates[:limit]
