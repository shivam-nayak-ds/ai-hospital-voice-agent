from typing import List
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from src.utils.logger import custom_logger as logger

class AshaReranker:
    """
    Reranker Service: Cross-checks retriever results for maximum accuracy.
    Uses a local Cross-Encoder model.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        logger.info(f"Loading Reranker model: {model_name}...")
        try:
            self.model = CrossEncoder(model_name)
            logger.success("Reranker model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Reranker: {e}")
            self.model = None

    def rerank(self, query: str, documents: List[Document], top_n: int = 3) -> List[Document]:
        """
        Reranks the candidates and returns the top_n most relevant ones.
        """
        if not self.model or not documents:
            return documents[:top_n]

        logger.info(f"Reranking {len(documents)} candidates for query: {query}")
        
        # Cross-Encoder maangta hai pairs: [(query, doc1), (query, doc2), ...]
        sentence_pairs = [[query, doc.page_content] for doc in documents]
        
        # Sabhi pairs ko score do
        scores = self.model.predict(sentence_pairs)
        
        # Docs aur scores ko ek saath jod kar sort karo
        results = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        
        # Sirf top_n results wapas bhejo
        reranked_docs = [res[0] for res in results[:top_n]]
        logger.info(f"Reranking complete. Best score: {max(scores):.4f}")
        
        return reranked_docs

if __name__ == "__main__":
    # Test Run
    from langchain_core.documents import Document
    reranker = AshaReranker()
    query = "What is MRI cost?"
    docs = [
        Document(page_content="MRI cost is 5000 INR."),
        Document(page_content="The hospital has a big garden."),
        Document(page_content="Insurance covers surgical procedures.")
    ]
    top_docs = reranker.rerank(query, docs)
    for d in top_docs:
        print(f"Result: {d.page_content}")
