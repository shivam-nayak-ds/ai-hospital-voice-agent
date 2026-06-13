import os
from config.settings import settings as main_settings

class RAGSettings:
    # Embedding config (BGE-base-en-v1.5 has 768 dimensions)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DIMENSION: int = 768
    
    QDRANT_HOST: str = main_settings.QDRANT_HOST
    QDRANT_PORT: str = main_settings.QDRANT_PORT
    QDRANT_URL: str = main_settings.QDRANT_URL
    QDRANT_API_KEY: str = main_settings.QDRANT_API_KEY
    
    # Collections
    FAQ_COLLECTION: str = "hospital_faqs"
    JSON_COLLECTION: str = "hospital_json_metadata"
    MARKDOWN_COLLECTION: str = "hospital_markdown_policies"
    
    # Search settings
    SIMILARITY_THRESHOLD: float = 0.35
    RERANK_THRESHOLD: float = 0.10

    # Offload configuration
    # Only offload to API if TEI endpoints or HF token are actually set.
    # Falls back to local SentenceTransformer / CrossEncoder otherwise.
    OFFLOAD_RAG_MODELS: bool = bool(os.getenv("TEI_EMBEDDING_URL") or os.getenv("TEI_RERANK_URL") or os.getenv("HF_API_TOKEN"))
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    TEI_EMBEDDING_URL: str = os.getenv("TEI_EMBEDDING_URL", "")
    TEI_RERANK_URL: str = os.getenv("TEI_RERANK_URL", "")

rag_settings = RAGSettings()
