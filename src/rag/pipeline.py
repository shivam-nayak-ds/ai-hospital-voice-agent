from src.rag.loader import DocumentLoader
from src.rag.metadata import MetadataManager # Naya Add hua
from src.rag.cleaner import TextCleaner
from src.rag.embedder import DataEmbedder
from src.rag.vectorstrore.db import VectorDBManager
from src.utils.logger import custom_logger as logger
from dotenv import load_dotenv

load_dotenv()

class RAGIngestionPipeline:
    def __init__(self):
        self.loader = DocumentLoader()
        self.metadata_mgr = MetadataManager() # Naya Add hua
        self.cleaner = TextCleaner()
        self.embedder = DataEmbedder()
        self.db_manager = VectorDBManager()

    def run(self):
        logger.info("---  Starting Asha's Knowledge Ingestion (with Metadata) ---")
        
        # 1. Load
        raw_docs = self.loader.load_data()
        if not raw_docs: return

        # 2. Enrich Metadata (NEW STEP)
        enriched_docs = self.metadata_mgr.enrich_metadata(raw_docs)

        # 3. Clean & Chunk
        final_chunks = self.cleaner.clean(enriched_docs)

        # 4. Embed
        embedding_func = self.embedder.get_embedding_function()
        
        # 5. Store
        self.db_manager.create_and_save(final_chunks, embedding_func)
        
        logger.info("---  SUCCESS: Knowledge Base updated with Metadata! ---")

if __name__ == "__main__":
    pipeline = RAGIngestionPipeline()
    pipeline.run()
