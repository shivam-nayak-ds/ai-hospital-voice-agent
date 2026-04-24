from src.rag.loader import DocumentLoader
from src.rag.cleaner import TextCleaner
from src.rag.embedder import DataEmbedder
from src.rag.vectorstrore.db import VectorDBManager
from src.utils.logger import custom_logger as logger
from dotenv import load_dotenv
import os

# API Keys load karna
load_dotenv()

class RAGIngestionPipeline:
    """
    The Master Pipeline: Connects all RAG components to build Asha's memory.
    """
    def __init__(self):
        self.loader = DocumentLoader()
        self.cleaner = TextCleaner()
        self.embedder = DataEmbedder()
        self.db_manager = VectorDBManager()

    def run(self):
        logger.info("--- 🚀 Starting Asha's Knowledge Ingestion Pipeline ---")
        
        # 1. Documents Load Karo
        raw_docs = self.loader.load_data()
        if not raw_docs:
            logger.error("Pipeline Aborted: No documents found to load.")
            return

        # 2. Clean & Chunk Karo
        final_chunks = self.cleaner.clean(raw_docs)
        if not final_chunks:
            logger.error("Pipeline Aborted: Chunking failed.")
            return

        # 3. Embedding Model Ready Karo (Google Gemini)
        embedding_func = self.embedder.get_embedding_function()
        
        # 4. Save to Vector Database
        self.db_manager.create_and_save(final_chunks, embedding_func)
        
        logger.info("--- ✅ SUCCESS: Asha is now smarter than ever! ---")

if __name__ == "__main__":
    pipeline = RAGIngestionPipeline()
    pipeline.run()
