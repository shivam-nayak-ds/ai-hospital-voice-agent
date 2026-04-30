from pydantic import BaseModel, Field
from typing import List, Optional, Dict, ClassVar
import uuid
import time

class PatientInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    symptoms: Optional[str] = None

class AshaState(BaseModel):
    """
    Asha's Multi-turn Conversation State & Memory
    """
    # 🏁 State Constants
    IDLE: ClassVar[str] = "IDLE"
    LISTENING: ClassVar[str] = "LISTENING"
    BOOKING: ClassVar[str] = "BOOKING_FLOW"
    EMERGENCY: ClassVar[str] = "EMERGENCY_MODE"

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_state: str = "IDLE"
    
    # 🧠 Memory & Context
    messages: List[Dict[str, str]] = Field(default_factory=list)
    patient: PatientInfo = Field(default_factory=PatientInfo)
    
    # 🛠️ Intent & Entities
    intent: str = "GENERAL"
    doctor_selected: Optional[str] = None
    appointment_time: Optional[str] = None
    
    # 📈 Metrics (50 LPA Standard)
    start_time: float = Field(default_factory=time.time)
    latency_logs: Dict[str, float] = Field(default_factory=dict)

    def reset_flow(self):
        self.current_state = self.IDLE
        self.doctor_selected = None
        self.appointment_time = None
        # 🔥 DO NOT reset patient info during a call! Let her remember the name.
