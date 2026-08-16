from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.planner import AshaPlanner
from src.agents.state import AgentState


@pytest.mark.asyncio
async def test_planner_validator_integration():
    planner = AshaPlanner()
    
    # Mock LLM and Validator database check to keep the test offline and fast
    mock_choice = MagicMock()
    mock_choice.message.content = '{"intent": "book_appointment", "extracted_entities": {"doctor_name": "Amit Kumar", "patient_phone": "9876543210"}}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    # Mock doctor validation to succeed
    mock_validate_doc = AsyncMock(return_value=(True, "Dr. Amit Kumar", None, []))
    
    state: AgentState = {
        "messages": [{"role": "user", "content": "Book appointment with Amit, phone 9876543210"}],
        "patient_phone": None,
        "otp_sent_to": None,
        "is_otp_verified": False,
        "current_intent": None,
        "next_node": None,
        "session_id": "test_session",
        "patient_name": None,
        "doctor_name": None,
        "specialization": None,
        "appointment_date": None,
        "appointment_time": None,
        "appointment_id": None,
        "speech_output": None,
        "validation_errors": {}
    }
    
    # Patch client and validation methods
    with patch("src.agents.ananya_agent.get_groq_client") as mock_groq, \
         patch("src.agents.validator.AshaValidator.validate_doctor", new=mock_validate_doc):
         
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        updates = await planner.run_nlu(state)
        
        # Verify NLU and Validator integrated successfully
        assert updates.get("current_intent") == "book_appointment"
        assert updates.get("doctor_name") == "Dr. Amit Kumar"
        assert updates.get("patient_phone") == "9876543210"
        assert updates.get("next_node") == "otp_verification_node" # requires OTP
