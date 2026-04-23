from pydantic import BaseModel , Field
from typing import List , Optional , Dict
import uuid

class PatientInfo(BaseModel):
    """Details of the patient being assited"""
    name : Optional[str] = None
    age : Optional[str] = None
    gender : Optional[str] = None
    phone_number : Optional[str] = None
    email: Optional[str] = None
    address : Optional[str] = None
    symptoms : Optional[str] = None
    history : Optional[str] = None


class AgentState(BaseModel):
    """
    Overall state for the agent's brain
    """
    session_id : str = Field(..., description="Unique  session ID")
    patient : PatientInfo = Field(default_factory=PatientInfo)

    # LLM Conversation History (So the AI remembers what was said)
    messages : List[Dict[str,str]] = Field(default_factory=list)

    # RAG Knowledge
    context_documents : List[str] = Field(default_factory=list)
    rag_context_text : str = ""

    # Actions & Extraction
    intent : str = "UNKNOWN"
    extracted_data : Dict[str, str] = Field(default_factory=dict)
    extracted_text : str = ""

    # Execution flow
    current_step : str = "start"
    booking_details : Dict[str, str] = Field(default_factory=dict)

    # Agent Output
    response_text : str = ""
    next_step : str = ""

    # Error Handling
    error_message : Optional[str] = None
    max_retries_exceeded : bool = False
    
