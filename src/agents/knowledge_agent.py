"""
knowledge_agent.py
------------------
KnowledgeAgent: Handles FAQs, Department details, and hospital guidelines.
Retrieves context from Qdrant/BM25 using retrieve_hospital_info and uses 
the LLM to formulate safe, voice-friendly answers.
Includes try-except guards and session bound logging.
"""

from typing import Dict, Any
from config.settings import settings
from src.utils.logger import custom_logger as logger
from src.tools.rag_tool import retrieve_hospital_info

class KnowledgeAgent:
    """
    Hospital FAQ and Policy specialist using RAG-backed LLM generation.
    Supports exception safety and trace logging.
    """
    def __init__(self):
        logger.success("KnowledgeAgent initialized.")

    async def run(self, query: str, state: Dict[str, Any]) -> Dict[str, Any]:
        session_id = state.get("session_id", "default")
        log = logger.bind(session_id=session_id)
        log.info(f"KnowledgeAgent running RAG query: '{query}'")
        
        try:
            # 1. Retrieve raw search results from hospital knowledge base
            rag_context = await retrieve_hospital_info(query, limit=3)
            
            if not rag_context or "error" in rag_context.lower() or "unavailable" in rag_context.lower():
                log.info("KnowledgeAgent: RAG tool failure or empty context. Bypassing LLM generation.")
                return {
                    "speech_output": "I am sorry, but I am unable to access the hospital information system at the moment. Please try again later or contact our front desk.",
                    "next_node": None
                }
                
            if "no relevant hospital policies" in rag_context.lower():
                log.info("KnowledgeAgent: No RAG context found, fallback warning.")
                return {
                    "speech_output": "I am sorry, I couldn't find any information on that in our knowledge base. Please call the hospital helpdesk at extension 100 for further assistance.",
                    "next_node": None
                }
                
            # 2. Formulate voice-optimized response using LLM
            from src.agents.ananya_agent import get_groq_client, get_gemini_client
            groq_client = get_groq_client()
            gemini_client = get_gemini_client()
            
            prompt = (
                "You are Ananya, a helpful receptionist at Lifeline Multi-Speciality Hospital.\n"
                "Your task is to answer the caller's question based strictly on the provided hospital knowledge base context.\n"
                "Follow these rules:\n"
                "1. Be extremely concise (under 2 sentences) and voice-friendly.\n"
                "2. Do not use markdown syntax, asterisks, or lists. Keep it in plain spoken paragraphs.\n"
                "3. If the context does not contain the answer, state that you don't know and suggest calling the front desk.\n"
                "4. NEVER give medical treatment, diagnoses, or drug prescriptions.\n\n"
                f"Knowledge Base Context:\n{rag_context}\n\n"
                f"User Question: {query}\n"
                "Spoken Response:"
            )
            
            response_text = ""
            
            # Try Groq
            if groq_client:
                try:
                    response = groq_client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response_text = response.choices[0].message.content.strip()
                    log.info("KnowledgeAgent LLM response generated successfully.")
                except Exception as e:
                    log.warning(f"KnowledgeAgent Groq generation failed: {e}")
                    
            # Try Gemini fallback
            if not response_text and gemini_client:
                try:
                    response = gemini_client.chat.completions.create(
                        model=settings.GEMINI_MODEL,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response_text = response.choices[0].message.content.strip()
                    log.info("KnowledgeAgent Gemini fallback generated successfully.")
                except Exception as e:
                    log.warning(f"KnowledgeAgent Gemini generation failed: {e}")
                    
            # Heuristic fallback if both fail
            if not response_text:
                log.info("KnowledgeAgent using hard retrieval context fallback.")
                response_text = "Based on our database: " + rag_context.split("\n")[1]
                
            # Clean up any potential markdown formatting in output
            response_text = response_text.replace("*", "").replace("#", "").strip()
            
            return {
                "speech_output": response_text,
                "next_node": "formatter_node"
            }
        except Exception as e:
            log.exception(f"Unhandled exception in KnowledgeAgent: {e}")
            return {
                "speech_output": "I am having trouble checking our information database right now. Please try again shortly.",
                "next_node": None
            }
