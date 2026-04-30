from typing import List
from langchain_core.documents import Document
from src.llm.providers.factory import LLMFactory # Humne Phase 2 mein banaya tha
from src.utils.logger import custom_logger as logger

class AshaGenerator:
    """
    Response Generator: Takes context and query to produce a grounded response.
    """
    def __init__(self):
        # We use our LLM Factory to get Groq
        self.llm = LLMFactory.get_provider("groq")

    def generate_response(self, query: str, context_docs: List[Document]) -> str:
        """
        Creates a prompt with context and generates the final answer.
        """
        if not context_docs:
            return "I'm sorry, I couldn't find any information about that in our hospital records."

        # 1. Context ko format karo (with Source/Page for grounding)
        context_text = ""
        for i, doc in enumerate(context_docs):
            source = doc.metadata.get("source", "Unknown")
            context_text += f"\nSnippet {i+1} (Source: {source}):\n{doc.page_content}\n"

        # 2. System Prompt taiyar karo
        prompt = f"""
        You are 'Asha', a professional and empathetic hospital assistant for City Care Hospital.
        Use the following retrieved context to answer the user's question.
        
        Rules:
        - If the answer is NOT in the context, say you don't know politely. Don't make things up.
        - Be concise and helpful.
        - Mention the department or service if applicable.
        
        CONTEXT:
        {context_text}
        
        USER QUESTION:
        {query}
        
        YOUR RESPONSE:
        """
        
        logger.info("Generating response from Groq...")
        try:
            response = self.llm.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now."

if __name__ == "__main__":
    # Internal Test
    from src.rag.query.retriever import AshaRetriever
    
    retriever = AshaRetriever()
    generator = AshaGenerator()
    
    query = "What services are available in the Emergency department?"
    docs = retriever.get_relevant_context(query)
    answer = generator.generate_response(query, docs)
    
    print(f"\n--- ASHA'S RESPONSE ---\n{answer}")
