from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import time

class ChatRequest(BaseModel):
    """Production Schema for incoming Chat/Voice requests"""
    
    session_id: str = Field(..., min_length=8, description="Unique Session ID for tracking conversation")
    user_id: Optional[str] = Field(None, description="Logged in User ID (if any)")
    message: str = Field(..., min_length=1, max_length=1000, description="User's text or STT output")
    
    # Metadata for better tracking
    timestamp: float = Field(default_factory=time.time)
    device_type: Optional[str] = Field("web", description="Device used: web, mobile, etc.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess-998877",
                "user_id": "user-123",
                "message": "Hello, I have a headache.",
                "device_type": "web"
            }
        }
    )
