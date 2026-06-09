import pytest
from unittest.mock import MagicMock, patch
from src.agents.planner import AshaPlanner

def test_determine_routing():
    planner = AshaPlanner()
    
    # 1. Secure intent, unverified -> otp_verification_node
    state = {"is_otp_verified": False}
    updates = {}
    assert planner.determine_routing("book_appointment", state, updates) == "otp_verification_node"
    assert planner.determine_routing("cancel_appointment", state, updates) == "otp_verification_node"
    assert planner.determine_routing("lab_report_status", state, updates) == "otp_verification_node"
    
    # 2. Secure intent, verified -> tools_node
    state_verified = {"is_otp_verified": True}
    assert planner.determine_routing("book_appointment", state_verified, updates) == "tools_node"
    
    # 3. Non-secure intents
    assert planner.determine_routing("emergency", state, updates) == "emergency_node"
    assert planner.determine_routing("chitchat", state, updates) == "chat_node"
    assert planner.determine_routing("faq", state, updates) == "rag_node"
    assert planner.determine_routing("billing_catalog", state, updates) == "tools_node"

@pytest.mark.asyncio
async def test_nlu_heuristics():
    planner = AshaPlanner()
    
    # Mock run_nlu dependencies to test heuristics when LLM fails/returns chitchat
    with patch("src.agents.ananya_agent.get_groq_client", return_value=None), \
         patch("src.agents.ananya_agent.get_gemini_client", return_value=None):
         
        # Test Timing queries fallback
        state1 = {"messages": [{"role": "user", "content": "What are the timings?"}]}
        updates1 = await planner.run_nlu(state1)
        assert updates1.get("current_intent") == "faq"
        
        # Test Address queries fallback
        state2 = {"messages": [{"role": "user", "content": "where is the hospital located?"}]}
        updates2 = await planner.run_nlu(state2)
        assert updates2.get("current_intent") == "faq"
        
        # Test Book appointment fallback
        state3 = {"messages": [{"role": "user", "content": "I want to reserve a slot"}]}
        updates3 = await planner.run_nlu(state3)
        assert updates3.get("current_intent") == "book_appointment"
