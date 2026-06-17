import json
import asyncio
from datetime import datetime
from typing import Generator, AsyncGenerator
from groq import Groq
from openai import OpenAI

from config.settings import settings
from src.agents.graph import get_agent_graph
from src.agents.state import AgentState
from src.utils.logger import custom_logger as logger

# ─── LLM Client Helpers (Singleton Cached) ──────────────────────────────────

_groq_client = None
_gemini_client = None
_CLIENT_TIMEOUT = 5  # seconds — fast fail when API is down


def get_groq_client() -> Groq | None:
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if settings.GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=settings.GROQ_API_KEY, timeout=_CLIENT_TIMEOUT, max_retries=0)
            return _groq_client
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
    return None


def get_gemini_client() -> OpenAI | None:
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if settings.GOOGLE_API_KEY:
        try:
            _gemini_client = OpenAI(
                api_key=settings.GOOGLE_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=_CLIENT_TIMEOUT,
                max_retries=0
            )
            return _gemini_client
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")
    return None


# ─── Intent Classifier ────────────────────────────────────────────────────────

class AshaIntentClassifier:
    """
    Intent Classifier for orchestrator routing.
    Determines intent for TTS prosody SSML generation and fast pre-checks.
    """
    def __init__(self):
        self.groq_client = get_groq_client()
        self.gemini_client = get_gemini_client()

    async def classify(self, text: str) -> tuple[str, float]:
        """
        Classifies user query transcript and returns (intent_name, confidence).
        Uses asyncio.to_thread to prevent blocking the event loop.
        Falls back to local rules on timeout or failure.
        """
        from src.agents.prompts import SYSTEM_ROUTER_PROMPT
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = SYSTEM_ROUTER_PROMPT.format(current_date=current_date)
        _CLASSIFY_TIMEOUT = 5  # 5s hard ceiling for intent classification
        
        # 1. Try Groq (Primary, fast) — wrapped in asyncio.to_thread
        if self.groq_client:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.groq_client.chat.completions.create,
                        model=settings.GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": text}
                        ],
                        response_format={"type": "json_object"}
                    ),
                    timeout=_CLASSIFY_TIMEOUT
                )
                data = json.loads(response.choices[0].message.content)
                return data.get("intent", "chitchat"), 1.0
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Groq intent classification failed ({type(e).__name__}): {e}")
                
        # 2. Try Gemini (Secondary, fallback) — wrapped in asyncio.to_thread
        if self.gemini_client:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.gemini_client.chat.completions.create,
                        model=settings.GEMINI_MODEL,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": text}
                        ],
                        response_format={"type": "json_object"}
                    ),
                    timeout=_CLASSIFY_TIMEOUT
                )
                data = json.loads(response.choices[0].message.content)
                return data.get("intent", "chitchat"), 1.0
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Gemini intent classification failed ({type(e).__name__}): {e}")
                
        # 3. Local Rule Fallback (instant, no API call)
        text_lower = text.lower()
        if "book" in text_lower or "appointment" in text_lower:
            return "book_appointment", 0.5
        if "doctor" in text_lower or "specialist" in text_lower:
            return "doctor_search", 0.5
        if "report" in text_lower or "lab" in text_lower:
            return "lab_report_status", 0.5
        if "emergency" in text_lower or "chest pain" in text_lower:
            return "emergency", 0.9
        return "chitchat", 0.5


# ─── Orchestrator Swarm ───────────────────────────────────────────────────────

class AshaSwarm:
    """
    Asha Swarm Orchestrator.
    Manages patient conversational sessions and executes the LangGraph state machine.
    Supports stateless operation: state can be injected from Redis for multi-worker compatibility.
    """
    def __init__(self, user_id: str, initial_state: dict = None):
        self.user_id = user_id
        self.graph = get_agent_graph()
        
        if initial_state:
            # Restore state from Redis (multi-worker safe)
            self.state: AgentState = initial_state
            logger.info(f"AshaSwarm restored state from Redis for session: {user_id}")
        else:
            # Initialize fresh session state (AgentState compliant)
            self.state: AgentState = {
                "messages": [],
                "session_id": user_id,
                "patient_name": None,
                "patient_phone": None,
                "doctor_name": None,
                "specialization": None,
                "appointment_date": None,
                "appointment_time": None,
                "appointment_id": None,
                "is_otp_verified": False,
                "otp_sent_to": None,
                "current_intent": None,
                "next_node": None,
                "speech_output": None
            }
            logger.success(f"AshaSwarm initialized new session for user: {user_id}")

    async def run(self, text: str) -> "AsyncGenerator[str, None]":
        """
        Executes a conversation turn by invoking LangGraph and streaming text tokens.
        """
        self.state["messages"].append({"role": "user", "content": text})
        
        try:
            # Execute LangGraph asynchronously using state input
            result = await self.graph.ainvoke(self.state)
            
            # Sync state with outputs
            self.state.update(result)
            
            speech_response = self.state.get("speech_output")
            if not speech_response:
                speech_response = "I am sorry, I am having trouble processing that right now."
                
            self.state["messages"].append({"role": "assistant", "content": speech_response})
            
            # Stream the response word-by-word
            words = speech_response.split(" ")
            for i, word in enumerate(words):
                if i < len(words) - 1:
                    yield word + " "
                else:
                    yield word
                    
        except Exception as e:
            logger.error(f"Error executing LangGraph workflow: {e}")
            yield "I encountered an issue processing your request. Please try again shortly."
