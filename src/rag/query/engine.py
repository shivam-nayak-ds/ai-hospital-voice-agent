from src.rag.query.retriever import AshaRetriever
from src.rag.query.reranker import AshaReranker
from src.rag.query.generator import AshaGenerator
from src.utils.logger import custom_logger as logger

class RAGQueryEngine:
    """
    RAG Query Engine: Orchestrates the Retrieval -> Rerank -> Generate flow.
    The single point of contact for the LLM Brain to get grounded answers.
    """
    def __init__(self):
        logger.info("Initializing RAG Query Engine...")
        self.retriever = AshaRetriever()
        self.reranker = AshaReranker()
        self.generator = AshaGenerator()
        logger.success("RAG Query Engine ready.")

    def query(self, user_question: str) -> str:
        """
        Executes the full RAG pipeline for a given question.
        """
        logger.info(f"--- Processing RAG Query: {user_question} ---")
        
        # 1. Retrieve (Get more candidates for reranking)
        initial_docs = self.retriever.get_relevant_context(user_question, top_k=10)
        
        if not initial_docs:
            return "I'm sorry, I don't have any information on that in my records."

        # 2. Rerank (Pick the absolute best 3)
        best_docs = self.reranker.rerank(user_question, initial_docs, top_n=3)
        
        # 3. Generate (Cook the final answer)
        final_answer = self.generator.generate_response(user_question, best_docs)
        
        logger.info("--- RAG Query Cycle Complete ---")
        return final_answer

if __name__ == "__main__":
    # Full System Test
    engine = RAGQueryEngine()
    print("\n\nTesting System...")
    response = engine.query("What are the ICU visiting hours and rules?")
    print(f"\nFINAL ANSWER:\n{response}")
