import json
from datetime import datetime
from typing import Generator, AsyncGenerator
from groq import Groq
from openai import OpenAI

from config.settings import settings
from src.agents.graph import get_agent_graph
from src.agents.state import AgentState
from src.utils.logger import custom_logger as logger

# ─── LLM Client Helpers ───────────────────────────────────────────────────────

def get_groq_client() -> Groq | None:
    if settings.GROQ_API_KEY:
        try:
            return Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
    return None

def get_gemini_client() -> OpenAI | None:
    if settings.GOOGLE_API_KEY:
        try:
            return OpenAI(
                api_key=settings.GOOGLE_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
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

    def classify(self, text: str) -> tuple[str, float]:
        """
        Classifies user query transcript and returns (intent_name, confidence).
        """
        from src.agents.prompts import SYSTEM_ROUTER_PROMPT
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = SYSTEM_ROUTER_PROMPT.format(current_date=current_date)
        
        # 1. Try Groq (Primary, fast)
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                return data.get("intent", "chitchat"), 1.0
            except Exception as e:
                logger.warning(f"Groq intent classification failed: {e}")
                
        # 2. Try Gemini (Secondary, fallback)
        if self.gemini_client:
            try:
                response = self.gemini_client.chat.completions.create(
                    model=settings.GEMINI_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text}
                    ],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                return data.get("intent", "chitchat"), 1.0
            except Exception as e:
                logger.warning(f"Gemini intent classification failed: {e}")
                
        # 3. Local Rule Fallback
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
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.graph = get_agent_graph()
        
        # Initialize session state (AgentState compliant)
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
        logger.success(f"AshaSwarm initialized successfully for user session: {user_id}")

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
