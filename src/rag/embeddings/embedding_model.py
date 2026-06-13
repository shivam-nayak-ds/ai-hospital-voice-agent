import asyncio
import httpx
from typing import List, Optional
from src.utils.logger import custom_logger as logger
from src.rag.config.settings import rag_settings

class EmbeddingModel:
    """
    Embedding Model Wrapper supporting both local SentenceTransformer execution
    and asynchronous offloaded inference via external APIs (Hugging Face or TEI).
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or rag_settings.EMBEDDING_MODEL_NAME
        self.model = None  # Lazily loaded SentenceTransformer model

    def _load_local_model(self) -> None:
        if self.model is not None:
            return
        # Force offline mode to use cached model (avoids SSL/network issues)
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local SentenceTransformer model as fallback: {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.success(f"Successfully loaded fallback local embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load fallback sentence-transformers model {self.model_name}: {e}")
            raise e

    async def _embed_via_api(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Queries external TEI server or Hugging Face Inference API for embeddings."""
        headers = {}
        if rag_settings.HF_API_TOKEN:
            headers["Authorization"] = f"Bearer {rag_settings.HF_API_TOKEN}"

        # Choose endpoint: TEI takes precedence if defined
        if rag_settings.TEI_EMBEDDING_URL:
            url = rag_settings.TEI_EMBEDDING_URL
            payload = {"inputs": texts}
        else:
            # Hugging Face Feature Extraction API
            url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
            payload = {"inputs": texts, "options": {"wait_for_model": True}}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    # HF returns list of floats for single text, or list of list of floats for batch
                    if isinstance(result, list):
                        if len(result) > 0 and isinstance(result[0], float) and len(texts) == 1:
                            return [result]
                        return result
                logger.warning(f"External embedding API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Failed to fetch embeddings from API: {e}")
        return None

    async def embed_text(self, text: str) -> List[float]:
        """
        Generates dense vector representation for a single text string.
        """
        if not text.strip():
            return []

        if rag_settings.OFFLOAD_RAG_MODELS:
            api_res = await self._embed_via_api([text])
            if api_res is not None and len(api_res) > 0:
                return api_res[0]
            logger.info("API embedding failed. Falling back to local SentenceTransformer.")

        # Fallback to local SentenceTransformer
        self._load_local_model()
        try:
            # Running local sentence transformer encoding (CPU-bound)
            # Wrap in asyncio.to_thread to avoid blocking the event loop
            embedding = await asyncio.to_thread(
                self.model.encode, text, convert_to_numpy=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate local embedding: {e}")
            raise e

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations for a list of text strings in batch.
        """
        if not texts:
            return []

        if rag_settings.OFFLOAD_RAG_MODELS:
            api_res = await self._embed_via_api(texts)
            if api_res is not None:
                return api_res
            logger.info("API batch embedding failed. Falling back to local SentenceTransformer.")

        # Fallback to local SentenceTransformer
        self._load_local_model()
        try:
            # Wrap CPU-bound encode in asyncio.to_thread
            embeddings = await asyncio.to_thread(
                self.model.encode, texts, show_progress_bar=False, convert_to_numpy=True
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate local batch embeddings: {e}")
            raise e
