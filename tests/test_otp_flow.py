import pytest
from src.agents.graph import otp_verification_node
from src.agents.state import AgentState

def test_otp_verification_flow_missing_phone():
    state: AgentState = {
        "messages": [{"role": "user", "content": "Book appointment"}],
        "patient_phone": None,
        "otp_sent_to": None,
        "is_otp_verified": False,
        "current_intent": "book_appointment",
        "next_node": "otp_verification_node",
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
    
    res = otp_verification_node(state)
    assert "tell me your ten digit registered mobile number" in res["speech_output"]
    assert res["next_node"] == "__end__"

def test_otp_verification_flow_trigger_otp():
    state: AgentState = {
        "messages": [{"role": "user", "content": "7089091461"}],
        "patient_phone": "7089091461",
        "otp_sent_to": None,
        "is_otp_verified": False,
        "current_intent": "book_appointment",
        "next_node": "otp_verification_node",
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
    
    res = otp_verification_node(state)
    assert res["otp_sent_to"] == "7089091461"
    assert "sent a four digit verification code" in res["speech_output"]
    assert res["next_node"] == "__end__"

def test_otp_verification_flow_invalid_otp():
    state: AgentState = {
        "messages": [{"role": "user", "content": "9999"}], # invalid OTP
        "patient_phone": "7089091461",
        "otp_sent_to": "7089091461",
        "is_otp_verified": False,
        "current_intent": "book_appointment",
        "next_node": "otp_verification_node",
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
    
    res = otp_verification_node(state)
    assert "incorrect" in res["speech_output"]
    assert res["next_node"] == "__end__"

def test_otp_verification_flow_valid_otp():
    state: AgentState = {
        "messages": [{"role": "user", "content": "Please verify 1234"}], # contains '1234'
        "patient_phone": "7089091461",
        "otp_sent_to": "7089091461",
        "is_otp_verified": False,
        "current_intent": "book_appointment",
        "next_node": "otp_verification_node",
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
    
    res = otp_verification_node(state)
    assert res["is_otp_verified"] is True
    assert "successful" in res["speech_output"]
    assert res["next_node"] == "tools_node"
