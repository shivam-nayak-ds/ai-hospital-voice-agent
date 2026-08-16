import asyncio

import httpx
from sentence_transformers import CrossEncoder

from src.rag.config.settings import rag_settings
from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class CrossEncoderReranker:
    """
    Reranks candidate documents using local BGE Cross-Encoder weights
    or offloads to external Text Embeddings Inference (TEI) / Hugging Face endpoints.
    Applies strict threshold filtering and features crash-resilient fallback systems.
    """
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None  # Lazily loaded to save memory if API offloading is active

    def _load_local_model(self) -> None:
        """
        Loads the cross encoder model on CPU/GPU only when required.
        """
        if self.model is not None:
            return
        # Force offline mode to use cached model (avoids SSL/network issues)
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        logger.info(f"Loading local Cross-Encoder reranker as fallback: {self.model_name}...")
        try:
            self.model = CrossEncoder(self.model_name)
            logger.success(f"Successfully loaded fallback Cross-Encoder: {self.model_name}")
        except Exception as e:
            logger.critical(f"Failed to load Cross-Encoder {self.model_name}: {e}.")
            raise e

    async def _rerank_via_api(self, query: str, texts: list[str]) -> list[float] | None:
        """
        Asynchronously queries an external TEI or HF Inference API for reranking scores.
        """
        headers = {}
        if rag_settings.HF_API_TOKEN:
            headers["Authorization"] = f"Bearer {rag_settings.HF_API_TOKEN}"

        # Production Grade: TEI (Text Embeddings Inference) Rerank Endpoint
        if rag_settings.TEI_RERANK_URL:
            url = rag_settings.TEI_RERANK_URL
            payload = {"query": query, "texts": texts}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        results = response.json()
                        # TEI returns: [{"index": 0, "score": 0.9}, {"index": 1, "score": 0.1}]
                        scores = [0.0] * len(texts)
                        for res in results:
                            scores[res["index"]] = res["score"]
                        return scores
                    logger.warning(f"TEI API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Failed to fetch TEI reranking scores: {e}")
        else:
            # Fallback to Hugging Face Inference API for sequence classification
            url = f"https://api-inference.huggingface.co/models/{self.model_name}"
            payload = {
                "inputs": {"source_sentence": query, "sentences": texts},
                "options": {"wait_for_model": True}
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        results = response.json()
                        # Extremely fault tolerant parsing
                        if isinstance(results, list):
                            # HF API usually returns a list of floats or list of lists
                            return [float(r) if not isinstance(r, list) else float(r[0]) for r in results]
                    logger.warning(f"HF API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Failed to fetch HF API reranking scores: {e}")
                
        return None

    async def rerank(
        self,
        query: str,
        candidates: list[Document],
        limit: int = 3,
        threshold: float = None
    ) -> list[Document]:
        """
        Asynchronously reranks candidates. Offloads to API if enabled,
        with seamless lazy-load fallback to local execution.
        """
        if not candidates:
            return []
        
        if not query.strip():
            return candidates[:limit]

        rerank_threshold = threshold if threshold is not None else rag_settings.RERANK_THRESHOLD
        texts = [doc.page_content for doc in candidates]
        scores = None

        # 1. Attempt API Offloading
        if rag_settings.OFFLOAD_RAG_MODELS:
            scores = await self._rerank_via_api(query, texts)
            if scores is None:
                logger.info("External Reranking API failed or unavailable. Falling back to local CrossEncoder.")

        # 2. Local Fallback Execution
        if scores is None:
            try:
                self._load_local_model()
                pairs = [[query.strip(), t] for t in texts]
                # Wrap sync CrossEncoder.predict in asyncio.to_thread
                local_scores = await asyncio.to_thread(self.model.predict, pairs)
                scores = [float(s) for s in local_scores]
            except Exception as e:
                logger.error(f"Error during fallback Cross-Encoder reranking: {e}.")
                logger.warning("Reranker completely failed. Returning top candidates in raw order.")
                return candidates[:limit]

        # 3. Enrich and Filter Candidates
        reranked_docs = []
        for doc, score in zip(candidates, scores):
            if score >= rerank_threshold:
                doc_copy = Document(page_content=doc.page_content, metadata=doc.metadata.copy())
                doc_copy.metadata.update({
                    "rerank_score": score,
                    "old_score": doc.metadata.get("score")
                })
                # Override principal score for sorting compatibility
                doc_copy.metadata["score"] = score
                reranked_docs.append(doc_copy)

        # 4. Sort and Return
        reranked_docs.sort(key=lambda d: d.metadata.get("rerank_score", 0.0), reverse=True)
        logger.info(f"Reranker: Filtered down to {len(reranked_docs)}/{len(candidates)} items (Threshold: {rerank_threshold})")
        
        return reranked_docs[:limit]
