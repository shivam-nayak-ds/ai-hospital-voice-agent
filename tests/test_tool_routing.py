import pytest
from src.agents.operations_agent import AshaOperationsAgent

@pytest.mark.asyncio
async def test_operations_agent_routing():
    ops_agent = AshaOperationsAgent()
    
    # 1. Lab Report Status missing phone
    state1 = {
        "current_intent": "lab_report_status",
        "patient_phone": None,
        "session_id": "test_session",
        "validation_errors": {}
    }
    res1 = await ops_agent.run(state1)
    assert "mobile number" in res1["speech_output"]
    assert res1["next_node"] is None
    
    # 2. Book appointment missing doctor
    state2 = {
        "current_intent": "book_appointment",
        "doctor_name": None,
        "session_id": "test_session",
        "validation_errors": {}
    }
    res2 = await ops_agent.run(state2)
    assert "Which doctor" in res2["speech_output"]
    assert res2["next_node"] is None

    # 3. Book appointment missing date
    state3 = {
        "current_intent": "book_appointment",
        "doctor_name": "Amit",
        "appointment_date": None,
        "session_id": "test_session",
        "validation_errors": {}
    }
    res3 = await ops_agent.run(state3)
    assert "For which date" in res3["speech_output"]
    assert res3["next_node"] is None
