from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.ananya_agent import AshaSwarm


@pytest.mark.asyncio
async def test_e2e_booking_flow():
    # Create Swarm instance for session
    swarm = AshaSwarm(user_id="test_e2e_user")
    
    # Pre-configure mock completions for each turn
    completions = [
        # Turn 1: "Book appointment"
        '{"intent": "book_appointment", "extracted_entities": {}}',
        # Turn 2: "7089091461"
        '{"intent": "chitchat", "extracted_entities": {"patient_phone": "7089091461"}}',
        # Turn 3: "1234"
        '{"intent": "chitchat", "extracted_entities": {}}',
        # Turn 4: "Amit"
        '{"intent": "doctor_search", "extracted_entities": {"doctor_name": "Amit"}}',
        # Turn 5: "tomorrow"
        '{"intent": "chitchat", "extracted_entities": {"appointment_date": "tomorrow"}}',
        # Turn 6: "10:00 AM"
        '{"intent": "chitchat", "extracted_entities": {"appointment_time": "10:00 AM"}}'
    ]
    
    mock_responses = []
    for comp in completions:
        mock_choice = MagicMock()
        mock_choice.message.content = comp
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_responses.append(mock_response)
        
    # Mock validation and services
    mock_validate_doc = AsyncMock(return_value=(True, "Dr. Amit Kumar", None, []))
    mock_validate_date = MagicMock(return_value=(True, "2026-06-11", None))
    mock_book = AsyncMock(return_value=(
        "Appointment confirmed! ID: 42 | Patient: Valued Patient | Doctor: Dr. Amit Kumar (Cardiology) | "
        "Date: 2026-06-11 | Time: 10:00 AM | Location: Cardiology Ward, Block A. Please arrive 15 minutes early."
    ))
    
    with patch("src.agents.ananya_agent.get_groq_client") as mock_groq, \
         patch("src.agents.validator.AshaValidator.validate_doctor", new=mock_validate_doc), \
         patch("src.agents.validator.AshaValidator.validate_date", new=mock_validate_date), \
         patch("src.agents.operations_agent.book_appointment", new=mock_book):
         
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_responses
        mock_groq.return_value = mock_client
        
        # Turn 1: Initial booking intent request
        res1 = ""
        async for token in swarm.run("Book appointment"):
            res1 += token
        assert "mobile number" in res1.lower()
        assert swarm.state["current_intent"] == "book_appointment"
        assert swarm.state["is_otp_verified"] is False
        
        # Turn 2: Provide phone number (routes to OTP verification)
        res2 = ""
        async for token in swarm.run("7089091461"):
            res2 += token
        assert "verification code" in res2.lower()
        assert swarm.state["patient_phone"] == "7089091461"
        assert swarm.state["otp_sent_to"] == "7089091461"
        
        # Turn 3: Verify OTP (success, routes to gather doctor name next)
        res3 = ""
        async for token in swarm.run("1234"):
            res3 += token
        assert "which doctor" in res3.lower()
        assert swarm.state["is_otp_verified"] is True
        
        # Turn 4: Provide Doctor (routes to gather date)
        res4 = ""
        async for token in swarm.run("Amit"):
            res4 += token
        assert "date" in res4.lower()
        assert swarm.state["doctor_name"] == "Dr. Amit Kumar"
        
        # Turn 5: Provide Date (routes to gather time slot)
        res5 = ""
        async for token in swarm.run("tomorrow"):
            res5 += token
        assert "time slot" in res5.lower()
        assert swarm.state["appointment_date"] == "2026-06-11"
        
        # Turn 6: Provide Time Slot (performs booking and returns confirmation message)
        res6 = ""
        async for token in swarm.run("10:00 AM"):
            res6 += token
        assert "appointment confirmed" in res6.lower()
        assert "location: cardiology ward, block a" in res6.lower()
