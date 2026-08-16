"""
state.py
--------
Defines the shared memory state (AgentState) for the AI Hospital Agent.
Tracks call history, extracted patient details, security states, and next-node actions.
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ─── Conversational Memory ────────────────────────────────────────────────
    # List of message dictionaries: [{"role": "user"|"assistant"|"system", "content": "..."}]
    messages: Annotated[list[dict[str, Any]], add_messages]
    session_id: str
    
    # ─── Entity Extraction Cache (Persisted Details) ────────────────────────
    # Saves parameters once extracted from speech, avoiding asking the user repeatedly.
    patient_name: str | None
    patient_phone: str | None
    doctor_name: str | None
    specialization: str | None
    appointment_date: str | None  # Format: YYYY-MM-DD
    appointment_time: str | None  # Format: e.g., "10:00 AM"
    appointment_id: int | None
    
    # ─── Security & Verification State ───────────────────────────────────────
    # Gates access to HIPAA-protected tools (lab reports, database inserts).
    is_otp_verified: bool
    otp_sent_to: str | None       # Phone number to which the last OTP was triggered
    
    # ─── Orchestration & Flow Control ────────────────────────────────────────
    # Stores the identified intent and the next graph node to execute
    current_intent: str | None    # e.g., "book_appointment", "check_lab_status", "faq"
    current_agent: str | None     # e.g., "supervisor", "booking", "knowledge", "billing", "lab", "emergency"
    next_node: str | None          # Node name: "tools_node", "verify_otp_node", "chat_node"
    validation_errors: dict[str, str] | None # Map of parameter -> error message
    
    # ─── Output Layer ────────────────────────────────────────────────────────
    # The final, short, speech-optimized response text sent to the TTS engine
    speech_output: str | None
