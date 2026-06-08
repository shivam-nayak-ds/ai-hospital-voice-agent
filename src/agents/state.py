"""
state.py
--------
Defines the shared memory state (AgentState) for the AI Hospital Agent.
Tracks call history, extracted patient details, security states, and next-node actions.
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # ─── Conversational Memory ────────────────────────────────────────────────
    # List of message dictionaries: [{"role": "user"|"assistant"|"system", "content": "..."}]
    messages: Annotated[List[Dict[str, Any]], add_messages]
    session_id: str
    
    # ─── Entity Extraction Cache (Persisted Details) ────────────────────────
    # Saves parameters once extracted from speech, avoiding asking the user repeatedly.
    patient_name: Optional[str]
    patient_phone: Optional[str]
    doctor_name: Optional[str]
    specialization: Optional[str]
    appointment_date: Optional[str]  # Format: YYYY-MM-DD
    appointment_time: Optional[str]  # Format: e.g., "10:00 AM"
    appointment_id: Optional[int]
    
    # ─── Security & Verification State ───────────────────────────────────────
    # Gates access to HIPAA-protected tools (lab reports, database inserts).
    is_otp_verified: bool
    otp_sent_to: Optional[str]       # Phone number to which the last OTP was triggered
    
    # ─── Orchestration & Flow Control ────────────────────────────────────────
    # Stores the identified intent and the next graph node to execute
    current_intent: Optional[str]    # e.g., "book_appointment", "check_lab_status", "faq"
    current_agent: Optional[str]     # e.g., "supervisor", "booking", "knowledge", "billing", "lab", "emergency"
    next_node: Optional[str]          # Node name: "tools_node", "verify_otp_node", "chat_node"
    validation_errors: Optional[Dict[str, str]] # Map of parameter -> error message
    
    # ─── Output Layer ────────────────────────────────────────────────────────
    # The final, short, speech-optimized response text sent to the TTS engine
    speech_output: Optional[str]
