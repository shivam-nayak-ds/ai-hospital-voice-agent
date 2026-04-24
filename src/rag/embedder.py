from langchain_huggingface import HuggingFaceEmbeddings
from src.utils.logger import custom_logger as logger

class DataEmbedder:
    """
    Hospital Data Embedder: Using Local HuggingFace model (Free & Reliable).
    """
    def __init__(self):
        # Hum local model use kar rahe hain (Ye 100% chalega)
        model_name = "all-MiniLM-L6-v2"
        logger.info(f"Initializing Local Embeddings with model: {model_name}...")
        
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
            logger.info("Local Embeddings initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Local Embeddings: {e}")
            raise

    def get_embedding_function(self):
        return self.embeddings

if __name__ == "__main__":
    embedder = DataEmbedder()
    print("Local Embedder is ready!")
