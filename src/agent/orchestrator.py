import re
import time
from typing import Optional
from src.agent.asha_agent import AshaAgent
from src.agent.state import AshaState
from src.utils.logger import custom_logger as logger

class AshaOrchestrator:
    """
    State-Based Decision Engine (50 LPA Standard)
    Handles logic flow, state transitions, and humanized delays.
    """

    SYMPTOM_MAP = {
        r"fever|bhukar|thand|cold|khansi|cough|body pain": "General Physician",
        r"heart|chest pain|dil|bp|blood pressure": "Cardiologist",
        r"skin|rash|khujli|dermatologist|face|pimples": "Dermatologist",
        r"bone|fracture|haddi|joint|ortho": "Orthopedic",
        r"bacha|child|kids|pediatric": "Pediatrician"
    }

    def __init__(self):
        self.agent = AshaAgent()
        self.state = AshaState()
        logger.success(" Asha State-Machine Orchestrator Ready")

    def _detect_intent(self, text: str) -> str:
        text = text.lower()

        # 1. Emergency Check (Top Priority)
        emergency_keywords = ["emergency", "accident", "khoon", "ambulance", "seene mein dard", "breathing problem"]
        if any(word in text for word in emergency_keywords):
            self.state.current_state = self.state.EMERGENCY
            return "emergency"

        # 2. Hardcoded Exit Intent
        exit_keywords = ["phone rakh", "rakh raha", "bye", "band kar", "stop", "disconnect", "rakhti hu", "baad me", "rakh rahi", "ja rahi"]
        if any(word in text for word in exit_keywords):
            return "exit"

        # 3. LLM-Based Smart Intent Classification
        try:
            prompt = f"Classify the user's intent into EXACTLY ONE word from this list: [booking, info, greeting].\nUser: {text}\nCategory:"
            response = self.agent.llm.client.chat.completions.create(
                model=self.agent.llm.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10
            )
            intent = response.choices[0].message.content.strip().lower()
            if "booking" in intent: 
                self.state.current_state = self.state.BOOKING
                return "appointment"
            if "info" in intent: return "general"
        except Exception as e:
            logger.warning(f"LLM Intent parsing failed, falling back. {e}")

        return "general"

    def _get_specialty(self, text: str) -> Optional[str]:
        for pattern, specialty in self.SYMPTOM_MAP.items():
            if re.search(pattern, text.lower()):
                return specialty
        return None

    def handle_request(self, user_input: str):
        # Humanize: Slight delay before processing (Step 5)
        time.sleep(0.4)
        
        intent = self._detect_intent(user_input)
        
        # 🔥 Intent-based reset: Exit stuck flows
        if hasattr(self.state, "intent") and self.state.intent != intent:
            self.state.reset_flow()
        self.state.intent = intent
        
        logger.info(f"State: {self.state.current_state} | Intent: {intent}")
        
        # 🔥 Name Extraction (Context Memory)
        name_match = re.search(r"mera naam (.*?) hai|i am (.*?)[\.\s]|my name is (.*?)[\.\s]|main (.*?) hu", user_input.lower() + " ")
        if name_match:
            extracted_name = next((m for m in name_match.groups() if m), None)
            if extracted_name:
                self.state.patient.name = extracted_name.strip().title()
                logger.success(f"Patient Name Extracted: {self.state.patient.name}")

        # Inject memory context
        if self.state.patient.name:
            user_input += f" [System Memory: The user's name is {self.state.patient.name}]"



        # Case 2: Off-topic Redirect
        if intent == "off_topic":
            user_input += " [SYSTEM: This is an off-topic or inappropriate query. Handle it politely and redirect to hospital services.]"

        # Case 3: Symptom Mapping
        specialty = self._get_specialty(user_input)
        if specialty:
            user_input += f" (Context: User likely needs {specialty})"

        # Case 4: LLM Brain Execution (Multi-Agent Hand-off)
        # We rely on LLM's natural Hinglish instead of hardcoded fillers for better prosody
        
        full_response = ""
        for token in self.agent.run(user_input, intent=intent):
            clean_token = token.replace("Certainly!", "").replace("Absolutely,", "")
            full_response += clean_token
            yield clean_token

        # State Cleanup: If flow completed, reset
        if "booked" in full_response.lower() or "confirm" in full_response.lower() or "theek hai" in full_response.lower():
            self.state.reset_flow()
            logger.info("Asha Flow Reset: Mission Accomplished.")