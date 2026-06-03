import time
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from src.utils.logger import custom_logger as logger
from config.settings import settings

class QdrantClientWrapper:
    """
    Wrapper for Qdrant client connection initialization with built-in retry logic.
    Supports both local host/port configurations and cloud URL/API Key configurations.
    """
    def __init__(self):
        self.host = settings.QDRANT_HOST
        self.port = int(settings.QDRANT_PORT)
        self._client = None

    def get_client(self, retries: int = 3, delay: float = 2.0) -> QdrantClient:
        """
        Connects to Qdrant server with retries. Returns QdrantClient instance.
        """
        if self._client:
            return self._client

        for attempt in range(1, retries + 1):
            try:
                if settings.QDRANT_URL and settings.QDRANT_API_KEY:
                    logger.info(f"Connecting to Qdrant Cloud Cluster (Attempt {attempt}/{retries})...")
                    client = QdrantClient(
                        url=settings.QDRANT_URL,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=10
                    )
                else:
                    logger.info(f"Connecting to local Qdrant at {self.host}:{self.port} (Attempt {attempt}/{retries})...")
                    client = QdrantClient(host=self.host, port=self.port, timeout=5)
                
                # Check connection health by querying collections
                client.get_collections()
                
                self._client = client
                if settings.QDRANT_URL and settings.QDRANT_API_KEY:
                    logger.success("Successfully connected to Qdrant Cloud Cluster!")
                else:
                    logger.success(f"Successfully connected to Qdrant at {self.host}:{self.port}")
                return self._client
            except Exception as e:
                logger.warning(f"Qdrant connection attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to connect to Qdrant after {retries} attempts.")
                    raise ConnectionError(f"Could not reach Qdrant server: {e}")

# Singleton connection provider
qdrant_provider = QdrantClientWrapper()
def get_qdrant_client() -> QdrantClient:
    return qdrant_provider.get_client()
