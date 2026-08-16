import asyncio
import os
import ssl
import time

from qdrant_client import AsyncQdrantClient, QdrantClient

from config.settings import settings
from src.utils.logger import custom_logger as logger

# ─── Fix Windows SSL Certificate Issue ────────────────────────────────────────
# Qdrant Cloud uses Let's Encrypt certs that Windows Python can't verify
# Create an unverified SSL context that skips certificate validation
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
except ImportError:
    pass

# Global unverified SSL context for Qdrant Cloud connections
_unverified_ssl = ssl.create_default_context()
_unverified_ssl.check_hostname = False
_unverified_ssl.verify_mode = ssl.CERT_NONE

class QdrantClientWrapper:
    """
    Wrapper for Qdrant client connection initialization with built-in retry logic.
    Supports both local host/port configurations and cloud URL/API Key configurations.
    Exposes both synchronous and asynchronous client connections.
    """
    def __init__(self):
        self.host = settings.QDRANT_HOST
        self.port = int(settings.QDRANT_PORT)
        self._client = None
        self._async_client = None

    def get_client(self, retries: int = 2, delay: float = 0.5) -> QdrantClient:
        """
        Connects to Qdrant server with retries. Returns QdrantClient instance.
        """
        if self._client:
            return self._client

        for attempt in range(1, retries + 1):
            try:
                if settings.QDRANT_URL and settings.QDRANT_API_KEY:
                    logger.info(f"Connecting to Qdrant Cloud Cluster (Attempt {attempt}/{retries})...")
                    # Use REST API with unverified SSL context (Windows Let's Encrypt issue)
                    client = QdrantClient(
                        url=settings.QDRANT_URL,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=10,
                        prefer_grpc=False,
                        verify=_unverified_ssl  # Skip SSL certificate verification
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

    async def get_async_client(self, retries: int = 3, delay: float = 2.0) -> AsyncQdrantClient:
        """
        Connects to Qdrant server asynchronously. Returns AsyncQdrantClient instance.
        """
        if self._async_client:
            return self._async_client

        for attempt in range(1, retries + 1):
            try:
                if settings.QDRANT_URL and settings.QDRANT_API_KEY:
                    logger.info(f"Connecting to Async Qdrant Cloud Cluster (Attempt {attempt}/{retries})...")
                    # Use REST API with unverified SSL context (Windows Let's Encrypt issue)
                    client = AsyncQdrantClient(
                        url=settings.QDRANT_URL,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=10,
                        prefer_grpc=False,
                        verify=_unverified_ssl  # Skip SSL certificate verification
                    )
                else:
                    logger.info(f"Connecting to local Async Qdrant at {self.host}:{self.port} (Attempt {attempt}/{retries})...")
                    client = AsyncQdrantClient(host=self.host, port=self.port, timeout=5)
                
                # Check connection health asynchronously
                await client.get_collections()
                
                self._async_client = client
                if settings.QDRANT_URL and settings.QDRANT_API_KEY:
                    logger.success("Successfully connected to Async Qdrant Cloud Cluster!")
                else:
                    logger.success(f"Successfully connected to Async Qdrant at {self.host}:{self.port}")
                return self._async_client
            except Exception as e:
                logger.warning(f"Async Qdrant connection attempt {attempt} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect to Async Qdrant after {retries} attempts.")
                    raise ConnectionError(f"Could not reach Async Qdrant server: {e}")

# Singleton connection provider
qdrant_provider = QdrantClientWrapper()

def get_qdrant_client() -> QdrantClient:
    return qdrant_provider.get_client()

async def get_async_qdrant_client() -> AsyncQdrantClient:
    return await qdrant_provider.get_async_client()
