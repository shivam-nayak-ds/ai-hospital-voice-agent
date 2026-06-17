"""
knowledge_agent.py
------------------
KnowledgeAgent: Handles FAQs, Department details, and hospital guidelines.
Retrieves context from Qdrant/BM25 using retrieve_hospital_info and uses 
the LLM to formulate safe, voice-friendly answers.

Includes an in-memory LRU cache to avoid expensive Qdrant + LLM calls
for repeated questions (e.g., "visiting hours" asked 100 times).
"""

from typing import Dict, Any
import asyncio
import hashlib
from functools import lru_cache
from config.settings import settings
from src.utils.logger import custom_logger as logger
from src.tools.rag_tool import retrieve_hospital_info

class KnowledgeAgent:
    """
    Hospital FAQ and Policy specialist using RAG-backed LLM generation.
    Includes in-memory cache for repeated queries to avoid redundant Qdrant + LLM calls.
    """
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._cache_max = 50  # Max cached answers in memory
        logger.success("KnowledgeAgent initialized with LRU cache.")

    def _cache_key(self, query: str) -> str:
        """Generate a normalized cache key from the query."""
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    async def run(self, query: str, state: Dict[str, Any]) -> Dict[str, Any]:
        session_id = state.get("session_id", "default")
        log = logger.bind(session_id=session_id)
        log.info(f"KnowledgeAgent running RAG query: '{query}'")
        
        try:
            # 0. Check cache first — avoid expensive Qdrant + LLM for repeated questions
            cache_key = self._cache_key(query)
            if cache_key in self._cache:
                log.info(f"KnowledgeAgent: Cache HIT for query: '{query}'")
                return {
                    "speech_output": self._cache[cache_key],
                    "next_node": "formatter_node"
                }
            
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
            _LLM_TIMEOUT = 7  # hard ceiling per LLM call
            
            # Try Groq with hard timeout
            if groq_client:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            groq_client.chat.completions.create,
                            model=settings.GROQ_MODEL,
                            messages=[{"role": "user", "content": prompt}]
                        ),
                        timeout=_LLM_TIMEOUT
                    )
                    response_text = response.choices[0].message.content.strip()
                    log.info("KnowledgeAgent LLM response generated successfully.")
                except (asyncio.TimeoutError, Exception) as e:
                    log.warning(f"KnowledgeAgent Groq failed ({type(e).__name__}): {e}")
                    
            # Try Gemini fallback with hard timeout
            if not response_text and gemini_client:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            gemini_client.chat.completions.create,
                            model=settings.GEMINI_MODEL,
                            messages=[{"role": "user", "content": prompt}]
                        ),
                        timeout=_LLM_TIMEOUT
                    )
                    response_text = response.choices[0].message.content.strip()
                    log.info("KnowledgeAgent Gemini fallback generated successfully.")
                except (asyncio.TimeoutError, Exception) as e:
                    log.warning(f"KnowledgeAgent Gemini failed ({type(e).__name__}): {e}")
                    
            # Heuristic fallback if both fail
            if not response_text:
                log.info("KnowledgeAgent using hard retrieval context fallback.")
                # Extract meaningful content from RAG — skip question/metadata lines
                lines = [l.strip() for l in rag_context.split("\n") if l.strip()]
                # Pick the longest content line (most likely to be the actual answer)
                answer_lines = [l for l in lines if len(l) > 30 and not l.lower().startswith("question")]
                if answer_lines:
                    response_text = answer_lines[0][:300]  # Cap at 300 chars for voice
                elif len(lines) > 2:
                    response_text = lines[2][:300]
                else:
                    response_text = "I found some information in our records, but I am unable to give a detailed answer right now. Please call the hospital helpdesk at extension 100."
                
            # Clean up any potential markdown formatting in output
            response_text = response_text.replace("*", "").replace("#", "").strip()
            
            # Store in cache (evict oldest if cache is full)
            if len(self._cache) >= self._cache_max:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = response_text
            
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
