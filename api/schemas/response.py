from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

class ChatResponse(BaseModel):
    """Production Schema for Agent responses"""
    
    session_id: str = Field(..., description="Session ID matching the request")
    response_text: str = Field(..., description="The main text response from AI")
    
    # Intelligence tracking
    intent_detected: Optional[str] = Field(None, description="The intent AI identified")
    suggested_actions: List[str] = Field(default_factory=list, description="Buttons/UI actions for frontend")
    
    # Performance & Monitoring
    status: str = Field("success", description="Response status: success/error")
    latency_ms: float = Field(0.0, description="Time taken to generate response")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess-998877",
                "response_text": "I'm sorry to hear that. How long have you had this headache?",
                "intent_detected": "symptom_reporting",
                "latency_ms": 450.5
            }
        }
    )

class ErrorResponse(BaseModel):
    """Standard Error Response for API"""
    error_code: str
    detail: str
    trace_id: Optional[str] = None # For log correlation
