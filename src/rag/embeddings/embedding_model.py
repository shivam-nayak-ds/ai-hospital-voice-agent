from sentence_transformers import SentenceTransformer
from typing import List
from src.utils.logger import custom_logger as logger
from src.rag.config.settings import rag_settings

class EmbeddingModel:
    """
    Local SentenceTransformer embedding model wrapper.
    Responsible for generating dense vector representations for queries and documents.
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or rag_settings.EMBEDDING_MODEL_NAME
        logger.info(f"Loading local SentenceTransformer model: {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.success(f"Successfully loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model {self.model_name}: {e}")
            raise e

    def embed_text(self, text: str) -> List[float]:
        """
        Generates dense vector representation for a single text string.
        """
        if not text.strip():
            return []
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations for a list of text strings in batch.
        """
        if not texts:
            return []
        try:
            embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise e
