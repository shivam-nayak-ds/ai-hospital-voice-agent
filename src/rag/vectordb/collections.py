from qdrant_client import QdrantClient
from qdrant_client.http import models
from src.utils.logger import custom_logger as logger
from src.rag.config.settings import rag_settings

def create_collection(client: QdrantClient, collection_name: str, vector_size: int = 768) -> None:
    """
    Creates a Qdrant collection if it does not already exist.
    Configures it with Cosine distance and payloads index.
    """
    try:
        collections_resp = client.get_collections()
        existing = [col.name for col in collections_resp.collections]
        
        if collection_name in existing:
            logger.info(f"Qdrant: Collection '{collection_name}' already exists.")
            return

        logger.info(f"Qdrant: Creating collection '{collection_name}' (vector size: {vector_size})...")
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        
        # Setup payload indexes for fast filtering
        logger.info(f"Qdrant: Setting up payload indexes for '{collection_name}'...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="category",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="department",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="type",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        
        logger.success(f"Qdrant: Collection '{collection_name}' initialized and indexed successfully.")

    except Exception as e:
        logger.error(f"Failed to create Qdrant collection '{collection_name}': {e}")
        raise e

def recreate_collection(client: QdrantClient, collection_name: str, vector_size: int = 768) -> None:
    """
    Force recreates a collection by deleting it first if it exists.
    """
    try:
        collections_resp = client.get_collections()
        existing = [col.name for col in collections_resp.collections]
        
        if collection_name in existing:
            logger.warning(f"Qdrant: Deleting existing collection '{collection_name}' for recreation...")
            client.delete_collection(collection_name=collection_name)
            
        create_collection(client, collection_name, vector_size)
    except Exception as e:
        logger.error(f"Failed to recreate collection '{collection_name}': {e}")
        raise e

def init_all_collections(client: QdrantClient) -> None:
    """
    Convenience runner to initialize all required system collections.
    """
    vector_size = rag_settings.EMBEDDING_DIMENSION
    create_collection(client, rag_settings.FAQ_COLLECTION, vector_size)
    create_collection(client, rag_settings.MARKDOWN_COLLECTION, vector_size)
