from typing import List, Optional
from langchain_core.documents import Document
from src.rag.vectorstrore.db import VectorDBManager
from src.rag.embedder import DataEmbedder
from src.utils.logger import custom_logger as logger

class AshaRetriever:
    """
    Asha Retrieval Service: Orchestrates semantic search across hospital documents.
    Designed for high-performance and reliable context fetching.
    """
    def __init__(self):
        self.db_manager = VectorDBManager()
        self.embedder = DataEmbedder()
        
        # Load embedding function (Google/Local)
        embedding_func = self.embedder.get_embedding_function()
        
        # Singleton-like DB connection
        self.vector_db = self.db_manager.load_db(embedding_func)
        if self.vector_db:
            logger.success("AshaRetriever: Knowledge Base loaded successfully.")
        else:
            logger.critical("AshaRetriever: Failed to load Knowledge Base. Did you run the pipeline?")

    def get_relevant_context(self, query: str, top_k: int = 4) -> List[Document]:
        """
        Retrieves the most relevant document chunks for a given user query.
        Args:
            query (str): User's natural language question.
            top_k (int): Number of chunks to retrieve.
        Returns:
            List[Document]: List of relevant LangChain documents.
        """
        if not self.vector_db:
            logger.error("Retrieval failed: Vector DB not initialized.")
            return []

        logger.info(f"Searching Knowledge Base for: '{query}'")
        
        try:
            # Semantic Similarity Search
            docs = self.vector_db.similarity_search(query, k=top_k)
            logger.info(f"Retrieved {len(docs)} candidate chunks.")
            return docs
            
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []

if __name__ == "__main__":
    # Internal Test Run
    retriever = AshaRetriever()
    test_query = "What are the emergency services available?"
    results = retriever.get_relevant_context(test_query)
    
    for i, doc in enumerate(results):
        print(f"\n--- Chunk {i+1} (Source: {doc.metadata.get('source')}) ---")
        print(doc.page_content[:200] + "...")
