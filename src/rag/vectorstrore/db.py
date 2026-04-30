import os
from langchain_chroma import Chroma
from src.utils.logger import custom_logger as logger

class VectorDBManager:
    """
    ChromaDB Manager: Handles saving and loading of Asha's knowledge base.
    """
    def __init__(self, db_path="data/chroma_db"):
        self.db_path = db_path

    def create_and_save(self, chunks, embedding_function):
        """Creates a new vector store from provided chunks."""
        logger.info(f"Creating Vector DB at: {self.db_path}")
        try:
            # We use Chroma.from_documents to create the database
            vector_db = Chroma.from_documents(
                documents=chunks,
                embedding=embedding_function,
                persist_directory=self.db_path
            )
            # Newer versions of Chroma auto-persist, but we log for success
            logger.info(f"Knowledge successfully saved to {self.db_path}")
            return vector_db
        except Exception as e:
            logger.error(f"Failed to create Vector DB: {e}")
            return None

    def load_db(self, embedding_function):
        """Loads the existing vector database from disk."""
        if not os.path.exists(self.db_path):
            logger.warning(f"No database found at {self.db_path}. Run pipeline first!")
            return None
            
        logger.info(f"Loading existing Knowledge Base from: {self.db_path}")
        return Chroma(
            persist_directory=self.db_path,
            embedding_function=embedding_function
        )
