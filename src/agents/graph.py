import random
import re
from typing import Any, Optional

from langgraph.graph import END, StateGraph

from config.settings import settings
from src.agents.guardrails import AshaGuardrails
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.memory import SessionMemoryManager
from src.agents.operations_agent import AshaOperationsAgent

# Import Multi-Agent Swarm Modules
from src.agents.planner import AshaPlanner
from src.agents.prompts import SYSTEM_CHAT_PROMPT
from src.agents.response_builder import AshaResponseBuilder
from src.agents.state import AgentState
from src.tools.emergency_tool import handle_emergency
from src.utils.logger import custom_logger as logger
from src.utils.message_helper import get_message_content

# Reusable agent and helper instances (cached to prevent recreation every turn)
_planner = AshaPlanner()
_memory_mgr = SessionMemoryManager()
_ops_agent = AshaOperationsAgent()
_knowledge_agent = KnowledgeAgent()
_response_builder = AshaResponseBuilder()

# ─── Production Redis OTP Store Helper ─────────────────────────────────────────
async def _store_redis_otp(session_id: str, otp_code: str, ttl_seconds: int = 300) -> bool:
    """Store 4-digit OTP in Redis with 5-minute automatic TTL expiration."""
    try:
        from src.agents.memory import get_session_store
        store = get_session_store()
        r = await store._get_redis()
        await r.set(f"asha:otp:{session_id}", otp_code, ex=ttl_seconds)
        return True
    except Exception as e:
        logger.warning(f"Redis OTP store error: {e}")
        return False

async def _get_redis_otp(session_id: str) -> Optional[str]:
    """Retrieve expected OTP code from Redis."""
    try:
        from src.agents.memory import get_session_store
        store = get_session_store()
        r = await store._get_redis()
        return await r.get(f"asha:otp:{session_id}")
    except Exception as e:
        logger.warning(f"Redis OTP retrieve error: {e}")
        return None

async def _delete_redis_otp(session_id: str) -> None:
    """Delete OTP from Redis upon successful verification."""
    try:
        from src.agents.memory import get_session_store
        store = get_session_store()
        r = await store._get_redis()
        await r.delete(f"asha:otp:{session_id}")
    except Exception as e:
        logger.warning(f"Redis OTP delete error: {e}")

def _dispatch_otp_sms(phone: str, otp_code: str) -> bool:
    """Dispatch real SMS via Twilio if credentials are configured, else fallback gracefully."""
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client as TwilioClient
            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f"Your Lifeline Hospital verification code is: {otp_code}. Valid for 5 minutes. Do not share this code.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=f"+91{phone.strip()[-10:]}"
            )
            logger.success(f"Twilio SMS OTP successfully dispatched to +91{phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch Twilio SMS OTP: {e}")
    else:
        logger.info(f"[SMS Sandbox/Dev] OTP '{otp_code}' for phone: +91{phone}")
    return False

# In-memory fallback if Redis is unreachable in local offline test mode
_pending_otps_fallback: dict[str, str] = {}


# ─── LangGraph Nodes ──────────────────────────────────────────────────────────

async def nlu_parser_node(state: AgentState) -> dict[str, Any]:
    """
    Supervisor Agent (Planner) Node: Sanitizes inputs, runs intent classification,
    extracts entities, and validates fields.
    """
    logger.info("LangGraph Node: NLU Parser (Supervisor)")
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_user_message = get_message_content(messages[-1])
    
    # 1. Pre-guardrail: Check input safety
    is_safe, sanitized_or_err = AshaGuardrails.inspect_input(last_user_message)
    if not is_safe:
        return {
            "speech_output": sanitized_or_err,
            "next_node": END
        }
        
    # 2. Prune old history turns to prevent context window bloat
    pruned_msgs = _memory_mgr.prune_messages(messages)
    # Inline update of messages state to prevent accumulating bloated threads
    state["messages"] = pruned_msgs
        
    # 3. Route & extract using Planner NLU
    updates = await _planner.run_nlu(state)
    return updates


async def otp_verification_node(state: AgentState) -> dict[str, Any]:
    """
    Verifies caller credentials via Redis-backed TTL OTP and Twilio SMS delivery.
    """
    logger.info("LangGraph Node: OTP Verification")
    patient_phone = state.get("patient_phone")
    otp_sent_to = state.get("otp_sent_to")
    session_id = state.get("session_id", "default")
    messages = state.get("messages", [])
    
    # 1. Ask for mobile number if missing
    if not patient_phone:
        return {
            "speech_output": "To access your profile or records, could you please tell me your ten digit registered mobile number?",
            "next_node": END
        }
        
    last_user_message = get_message_content(messages[-1]) if messages else ""
    
    # 2. Generate and dispatch OTP if phone is set but not yet sent
    if not otp_sent_to or otp_sent_to != patient_phone:
        otp_code = str(random.randint(1000, 9999))
        
        # Store in Redis with 5-minute (300s) TTL
        stored = await _store_redis_otp(session_id, otp_code, ttl_seconds=300)
        if not stored:
            _pending_otps_fallback[session_id] = otp_code
            
        # Dispatch SMS via Twilio
        _dispatch_otp_sms(patient_phone, otp_code)
        
        logger.success(f"OTP '{otp_code}' generated and sent to phone: {patient_phone}")
        return {
            "otp_sent_to": patient_phone,
            "speech_output": "I have sent a four digit verification code to your registered mobile number. Please say or enter the code to verify your identity.",
            "next_node": END
        }
        
    # 3. Check for 4-digit code in user input
    digits = re.findall(r"\b\d{4}\b", last_user_message)
    if digits:
        entered_otp = digits[0]
        expected_otp = await _get_redis_otp(session_id)
        if not expected_otp:
            expected_otp = _pending_otps_fallback.get(session_id)
        
        if expected_otp and entered_otp == expected_otp:
            logger.success(f"OTP verified successfully for session {session_id}")
            await _delete_redis_otp(session_id)
            _pending_otps_fallback.pop(session_id, None)
            
            # Determine next node dynamically based on original intent
            intent = state.get("current_intent")
            next_node = "tools_node"
            if intent in ["billing_catalog", "ward_availability", "insurance_cashless"]:
                next_node = "tools_node"
            elif intent == "emergency":
                next_node = "emergency_node"
            elif intent == "chitchat":
                next_node = "chat_node"
                
            return {
                "is_otp_verified": True,
                "speech_output": "Thank you. Verification successful.",
                "next_node": next_node
            }
        else:
            return {
                "speech_output": "The verification code you entered is incorrect. Please check your messages and say the code again.",
                "next_node": END
            }
    else:
        return {
            "speech_output": "Please state the four digit verification code to verify your identity.",
            "next_node": END
        }


async def tools_node(state: AgentState) -> dict[str, Any]:
    """
    Invokes specific structured tools based on mapped NLU intents.
    """
    logger.info("LangGraph Node: Database Tools Execution (Operations)")
    res = await _ops_agent.run(state)
    return res


async def chat_node(state: AgentState) -> dict[str, Any]:
    """
    Handles friendly greeting and general chitchat conversation.
    Async to prevent blocking the event loop during LLM API calls.
    """
    import asyncio
    logger.info("LangGraph Node: Chat Personas")
    messages = state.get("messages", [])
    
    from src.agents.ananya_agent import get_gemini_client, get_groq_client
    from src.utils.message_helper import convert_messages_to_dicts
    
    groq_client = get_groq_client()
    gemini_client = get_gemini_client()
    
    prompt = SYSTEM_CHAT_PROMPT
    last_msg = get_message_content(messages[-1]).lower().strip() if messages else ""
    
    # Smart local patterns — instant response, skip LLM entirely
    local_matched = False
    if any(w in last_msg for w in ["hi", "hello", "hey", "namaste", "good morning", "good evening"]):
        response_text = "Hello! I am Ananya, your virtual hospital assistant. How can I help you today?"
        local_matched = True
    elif any(w in last_msg for w in ["how are you", "how r u", "kaise ho", "kya haal"]):
        response_text = "I am doing great, thank you for asking! How can I assist you with Lifeline Hospital today?"
        local_matched = True
    elif any(w in last_msg for w in ["thank", "thanks", "dhanyavad", "shukriya"]):
        response_text = "You are most welcome! Is there anything else I can help you with?"
        local_matched = True
    elif any(w in last_msg for w in ["bye", "goodbye", "alvida"]):
        response_text = "Goodbye! Thank you for calling Lifeline Hospital. Have a wonderful day."
        local_matched = True
    elif any(w in last_msg for w in ["your name", "who are you", "kaun ho", "tumhara naam"]):
        response_text = "I am Ananya, the virtual assistant at Lifeline Multi-Speciality Hospital. How may I help you?"
        local_matched = True
    elif any(w in last_msg for w in ["what can you do", "help me with", "how can you help", "kya kar sakti"]):
        response_text = "I can help you book appointments, find doctors, check lab reports, answer hospital FAQs, and more. What would you like to do?"
        local_matched = True
    else:
        response_text = "I understand. Could you please rephrase that or tell me how I can assist you today?"
    
    if local_matched:
        logger.info("Chat node: local pattern matched, skipping LLM call")
        return {
            "speech_output": response_text,
            "next_node": END
        }
    
    # Only call LLM for complex/unmatched chitchat
    history_dicts = convert_messages_to_dicts(messages[-5:])
    llm_messages = [{"role": "system", "content": prompt}] + history_dicts
    
    groq_success = False
    _LLM_TIMEOUT = 7  # hard ceiling per LLM call
    
    # 1. Try Groq — wrapped in asyncio.to_thread with hard timeout
    if groq_client:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    groq_client.chat.completions.create,
                    model=settings.GROQ_MODEL,
                    messages=llm_messages
                ),
                timeout=_LLM_TIMEOUT
            )
            response_text = response.choices[0].message.content
            groq_success = True
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Groq chat failed ({type(e).__name__}): {e}")
            
    # 2. Try Gemini Fallback (only if Groq didn't timeout — avoids 2x wait)
    if not groq_success and gemini_client:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_client.chat.completions.create,
                    model=settings.GEMINI_MODEL,
                    messages=llm_messages
                ),
                timeout=_LLM_TIMEOUT
            )
            response_text = response.choices[0].message.content
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Gemini chat failed ({type(e).__name__}): {e}")
            
    return {
        "speech_output": response_text,
        "next_node": END
    }


async def rag_node(state: AgentState) -> dict[str, Any]:
    """
    Performs vector-based retrieval on hospital policy / FAQ knowledge base.
    """
    logger.info("LangGraph Node: RAG Knowledge Base Retrieval")
    messages = state.get("messages", [])
    query = get_message_content(messages[-1]) if messages else ""
    
    res = await _knowledge_agent.run(query, state)
    return res


def emergency_node(state: AgentState) -> dict[str, Any]:
    """
    Flags critical emergencies instantly.
    """
    logger.info("LangGraph Node: Emergency Gate")
    messages = state.get("messages", [])
    query = get_message_content(messages[-1]) if messages else ""
    result = handle_emergency(query)
    
    return {
        "speech_output": result,
        "next_node": END
    }


def formatter_node(state: AgentState) -> dict[str, Any]:
    """
    Instant speech formatting using local heuristic rules (no LLM call).
    Runs post-execution medical guardrails check.
    Executes in <1ms — does not block the event loop.
    """
    logger.info("LangGraph Node: Speech Formatter & Guardrails")
    raw_output = state.get("speech_output", "")
    if not raw_output:
        return {"next_node": END}
        
    # 1. Speech formatting (instant local heuristic — no LLM API call)
    formatted_speech = _response_builder.format_speech(raw_output, session_id=state.get("session_id", "default"))
    
    # 2. Post-guardrail verification
    compliant_speech = AshaGuardrails.inspect_output(formatted_speech)
            
    return {
        "speech_output": compliant_speech,
        "next_node": END
    }


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_graph(state: AgentState) -> str:
    val = state.get("next_node")
    return val if val else END


# ─── Graph Compilation ────────────────────────────────────────────────────────

def get_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Register Nodes
    workflow.add_node("nlu_parser", nlu_parser_node)
    workflow.add_node("otp_verification_node", otp_verification_node)
    workflow.add_node("tools_node", tools_node)
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("emergency_node", emergency_node)
    workflow.add_node("formatter_node", formatter_node)
    
    # Define Entry Point
    workflow.set_entry_point("nlu_parser")
    
    # Define Conditional Mappings
    workflow.add_conditional_edges(
        "nlu_parser",
        route_graph,
        {
            "otp_verification_node": "otp_verification_node",
            "emergency_node": "emergency_node",
            "chat_node": "chat_node",
            "rag_node": "rag_node",
            "tools_node": "tools_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "otp_verification_node",
        route_graph,
        {
            "tools_node": "tools_node",
            "chat_node": "chat_node",
            "emergency_node": "emergency_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "tools_node",
        route_graph,
        {
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "rag_node",
        route_graph,
        {
            "formatter_node": "formatter_node",
            END: END
        }
    )
    
    # Regular Edges
    workflow.add_edge("chat_node", END)
    workflow.add_edge("emergency_node", END)
    workflow.add_edge("formatter_node", END)
    
    return workflow.compile()
