"""
embedding_pipeline.py
---------------------
High-level orchestrator for embedding generation.

This module provides a `EmbeddingPipeline` that wraps the lower-level
`EmbeddingModel` and exposes a simple interface used by the ingestion
scripts to convert `Document` objects into Qdrant-ready float vectors.
"""

from src.rag.embeddings.embedding_model import EmbeddingModel
from src.rag.loaders.documents import Document
from src.utils.logger import custom_logger as logger


class EmbeddingPipeline:
    """
    Converts a list of `Document` objects to (Document, vector) pairs
    ready for upsert into Qdrant.

    Args:
        batch_size: Number of documents embedded per API/model call.
                    Smaller batches reduce memory pressure; larger batches
                    are faster on GPU or remote TEI endpoints.
    """

    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self._model = EmbeddingModel()

    async def run(self, documents: list[Document]) -> list[tuple[Document, list[float]]]:
        """
        Embeds all documents in batches.

        Returns:
            List of (Document, embedding_vector) tuples.
            Documents that fail to embed are skipped and logged.
        """
        if not documents:
            return []

        results: list[tuple[Document, list[float]]] = []
        total = len(documents)
        logger.info(f"EmbeddingPipeline: embedding {total} documents in batches of {self.batch_size}.")

        for start in range(0, total, self.batch_size):
            batch = documents[start: start + self.batch_size]
            texts = [doc.page_content for doc in batch]

            try:
                vectors = await self._model.embed_documents(texts)
                for doc, vec in zip(batch, vectors):
                    results.append((doc, vec))
            except Exception as e:
                logger.error(
                    f"EmbeddingPipeline: batch [{start}:{start + len(batch)}] failed: {e}. "
                    "Skipping batch."
                )

        logger.success(f"EmbeddingPipeline: completed — {len(results)}/{total} documents embedded.")
        return results

    async def embed_single(self, text: str) -> list[float]:
        """Convenience wrapper to embed a single query string (used at retrieval time)."""
        return await self._model.embed_text(text)
