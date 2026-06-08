import json
import re
from datetime import datetime
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END

from config.settings import settings
from src.agents.state import AgentState
from src.agents.prompts import SYSTEM_ROUTER_PROMPT, SYSTEM_CHAT_PROMPT, SPEECH_FORMATTER_PROMPT
from src.utils.logger import custom_logger as logger

# Import Multi-Agent Swarm Modules
from src.agents.planner import AshaPlanner
from src.agents.operations_agent import AshaOperationsAgent
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.guardrails import AshaGuardrails
from src.agents.response_builder import AshaResponseBuilder
from src.agents.validator import AshaValidator
from src.agents.memory import SessionMemoryManager

# Import database and emergency tools
from src.tools.emergency_tool import handle_emergency


# ─── LangGraph Nodes ──────────────────────────────────────────────────────────

async def nlu_parser_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor Agent (Planner) Node: Sanitizes inputs, runs intent classification,
    extracts entities, and validates fields.
    """
    logger.info("LangGraph Node: NLU Parser (Supervisor)")
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_user_message = messages[-1]["content"]
    
    # 1. Pre-guardrail: Check input safety
    is_safe, sanitized_or_err = AshaGuardrails.inspect_input(last_user_message)
    if not is_safe:
        return {
            "speech_output": sanitized_or_err,
            "next_node": END
        }
        
    # 2. Prune old history turns to prevent context window bloat
    memory_mgr = SessionMemoryManager()
    pruned_msgs = memory_mgr.prune_messages(messages)
    # Inline update of messages state to prevent accumulating bloated threads
    state["messages"] = pruned_msgs
        
    # 3. Route & extract using Planner NLU
    planner = AshaPlanner()
    updates = await planner.run_nlu(state)
    return updates


def otp_verification_node(state: AgentState) -> Dict[str, Any]:
    """
    Verifies caller credentials via SMS OTP (Mock verification).
    """
    logger.info("LangGraph Node: OTP Verification")
    patient_phone = state.get("patient_phone")
    otp_sent_to = state.get("otp_sent_to")
    messages = state.get("messages", [])
    
    # 1. Ask for mobile number if missing
    if not patient_phone:
        return {
            "speech_output": "To access your profile or records, could you please tell me your ten digit registered mobile number?",
            "next_node": END
        }
        
    last_user_message = messages[-1]["content"] if messages else ""
    
    # 2. Trigger OTP if phone is set but not yet texted
    if not otp_sent_to or otp_sent_to != patient_phone:
        logger.success(f"OTP '1234' sent to mobile number: {patient_phone}")
        return {
            "otp_sent_to": patient_phone,
            "speech_output": "I have sent a four digit verification code to your phone number. Please say or enter the code to verify your identity.",
            "next_node": END
        }
        
    # 3. Check for 4-digit code in user input
    digits = re.findall(r"\b\d{4}\b", last_user_message)
    if digits:
        entered_otp = digits[0]
        if entered_otp == "1234":  # Mock verification check
            logger.success("MFA OTP Verified successfully!")
            
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


async def tools_node(state: AgentState) -> Dict[str, Any]:
    """
    Invokes specific structured tools based on mapped NLU intents.
    """
    logger.info("LangGraph Node: Database Tools Execution (Operations)")
    ops_agent = AshaOperationsAgent()
    res = await ops_agent.run(state)
    return res


def chat_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles friendly greeting and general chitchat conversation.
    """
    logger.info("LangGraph Node: Chat Personas")
    messages = state.get("messages", [])
    
    from src.agents.ananya_agent import get_groq_client, get_openai_client
    groq_client = get_groq_client()
    openai_client = get_openai_client()
    
    prompt = SYSTEM_CHAT_PROMPT
    response_text = "Hello! I am Ananya, your virtual hospital assistant. How can I help you today?"
    
    # 1. Try Groq
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "system", "content": prompt}] + messages[-5:]
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq chat response failed: {e}")
            
    # 2. Try OpenAI Fallback
    if response_text == "Hello! I am Ananya, your virtual hospital assistant. How can I help you today?" and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}] + messages[-5:]
            )
            response_text = response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI chat response failed: {e}")
            
    return {
        "speech_output": response_text,
        "next_node": END
    }


def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Performs vector-based retrieval on hospital policy / FAQ knowledge base.
    """
    logger.info("LangGraph Node: RAG Knowledge Base Retrieval")
    messages = state.get("messages", [])
    query = messages[-1]["content"] if messages else ""
    
    knowledge_agent = KnowledgeAgent()
    res = knowledge_agent.run(query, state)
    return res


def emergency_node(state: AgentState) -> Dict[str, Any]:
    """
    Flags critical emergencies instantly.
    """
    logger.info("LangGraph Node: Emergency Gate")
    messages = state.get("messages", [])
    query = messages[-1]["content"] if messages else ""
    result = handle_emergency(query)
    
    return {
        "speech_output": result,
        "next_node": END
    }


def formatter_node(state: AgentState) -> Dict[str, Any]:
    """
    Uses Speech Formatter instructions to format output for phone playback and 
    runs post-execution medical guardrails check.
    """
    logger.info("LangGraph Node: Speech Formatter & Guardrails")
    raw_output = state.get("speech_output", "")
    if not raw_output:
        return {"next_node": END}
        
    # 1. Speech formatting
    builder = AshaResponseBuilder()
    formatted_speech = builder.format_speech(raw_output, session_id=state.get("session_id", "default"))
    
    # 2. Post-guardrail verification
    compliant_speech = AshaGuardrails.inspect_output(formatted_speech)
            
    return {
        "speech_output": compliant_speech,
        "next_node": END
    }


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_graph(state: AgentState) -> str:
    return state.get("next_node", END)


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
