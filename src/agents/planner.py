"""
planner.py
----------
Defines the Supervisor Agent (AshaPlanner) which acts as the orchestrator.
Responsible for:
1. LLM-based NLU classification of intent.
2. Structured entity extraction (phone, doctor, specialization, date, time).
3. Resolving relative inputs and validating parameters using AshaValidator.
4. Setting routing directives (next node, target agent).
Includes try-except guards and bound trace logging.
"""

import json
from datetime import datetime
from typing import Dict, Any, Tuple
from config.settings import settings
from src.agents.state import AgentState
from src.agents.validator import AshaValidator
from src.utils.logger import custom_logger as logger

class AshaPlanner:
    """
    Supervisor Agent that coordinates conversation flow and routes user queries.
    """
    def __init__(self):
        logger.success("AshaPlanner Supervisor initialized.")

    async def run_nlu(self, state: AgentState) -> Dict[str, Any]:
        """
        Runs the NLU extraction step to determine intent and entities.
        Updates state with the parsed parameters and validates them.
        """
        session_id = state.get("session_id", "default")
        log = logger.bind(session_id=session_id)
        log.info("Supervisor Agent (Planner) analyzing user query.")

        try:
            messages = state.get("messages", [])
            if not messages:
                return {}

            # Import LLM client helpers locally to avoid circular dependencies
            from src.agents.ananya_agent import get_groq_client, get_openai_client
            groq_client = get_groq_client()
            openai_client = get_openai_client()
            
            from src.agents.prompts import SYSTEM_ROUTER_PROMPT
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = SYSTEM_ROUTER_PROMPT.format(current_date=current_date)
            
            last_user_message = messages[-1]["content"]
            intent = "chitchat"
            entities = {}
            
            # 1. Groq (Primary router)
            if groq_client:
                try:
                    response = groq_client.chat.completions.create(
                        model=settings.GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": last_user_message}
                        ],
                        response_format={"type": "json_object"}
                    )
                    data = json.loads(response.choices[0].message.content)
                    intent = data.get("intent", "chitchat")
                    entities = data.get("extracted_entities", {})
                    log.info(f"Groq intent classified as: '{intent}'")
                except Exception as e:
                    log.warning(f"Groq NLU extraction failed: {e}")
                    
            # 2. OpenAI Fallback
            if intent == "chitchat" and openai_client:
                try:
                    response = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": last_user_message}
                        ],
                        response_format={"type": "json_object"}
                    )
                    data = json.loads(response.choices[0].message.content)
                    intent = data.get("intent", "chitchat")
                    entities = data.get("extracted_entities", {})
                    log.info(f"OpenAI fallback intent classified as: '{intent}'")
                except Exception as e:
                    log.warning(f"OpenAI NLU extraction failed: {e}")
                    
            # 3. Heuristic Rules (Backup)
            if not entities and intent == "chitchat":
                text_lower = last_user_message.lower()
                if any(w in text_lower for w in ["book", "appointment", "reserve", "slot"]):
                    intent = "book_appointment"
                elif any(w in text_lower for w in ["doctor", "specialist", "timings", "schedule"]):
                    intent = "doctor_search"
                elif any(w in text_lower for w in ["report", "lab", "test status"]):
                    intent = "lab_report_status"
                elif any(w in text_lower for w in ["emergency", "chest pain", "bleeding"]):
                    intent = "emergency"
                elif any(w in text_lower for w in ["price", "cost", "billing", "charges"]):
                    intent = "billing_catalog"
                    
            # Compile state updates
            updates: Dict[str, Any] = {"current_intent": intent}
            validation_errors: Dict[str, str] = {}
            
            # Merge existing entities with new ones if new ones are provided
            for key in ["patient_name", "patient_phone", "doctor_name", "specialization", "appointment_date", "appointment_time", "appointment_id"]:
                val = entities.get(key) if entities else None
                current_val = state.get(key)
                if val is None:
                    val = current_val
                    
                if val is not None:
                    if key == "patient_phone":
                        valid, phone_clean, err = AshaValidator.validate_phone(val)
                        if valid:
                            updates["patient_phone"] = phone_clean
                        else:
                            validation_errors["patient_phone"] = err
                            updates["patient_phone"] = None
                            
                    elif key == "appointment_date":
                        valid, date_clean, err = AshaValidator.validate_date(val)
                        if valid:
                            updates["appointment_date"] = date_clean
                        else:
                            validation_errors["appointment_date"] = err
                            updates["appointment_date"] = None
                            
                    elif key == "doctor_name":
                        valid, doc_clean, err, matches = await AshaValidator.validate_doctor(val)
                        if valid:
                            updates["doctor_name"] = doc_clean
                        else:
                            validation_errors["doctor_name"] = err
                            updates["doctor_name"] = None
                    else:
                        updates[key] = val
                        
            # Update validation errors
            updates["validation_errors"] = validation_errors
            
            # Determine Routing Agent Node
            updates["next_node"] = self.determine_routing(intent, state, updates)
            return updates

        except Exception as e:
            log.exception(f"Exception in Supervisor Planner NLU execution: {e}")
            # Fallback to chat node in case of supervisor failure
            return {
                "current_intent": "chitchat",
                "next_node": "chat_node",
                "validation_errors": {}
            }

    def determine_routing(self, intent: str, state: AgentState, updates: Dict[str, Any]) -> str:
        """
        Determines the next agent node based on the intent and verification status.
        Encapsulates safety gates (OTP requirement).
        """
        is_otp_verified = state.get("is_otp_verified", False) or updates.get("is_otp_verified", False)
        
        # Secure operations require OTP
        secure_intents = ["lab_report_status", "book_appointment", "cancel_appointment"]
        
        if intent in secure_intents and not is_otp_verified:
            logger.info(f"Route Check: Intent '{intent}' requires OTP. Routing to otp_verification_node.")
            return "otp_verification_node"
            
        if intent == "emergency":
            return "emergency_node"
            
        if intent == "chitchat":
            return "chat_node"
            
        if intent in ["billing_catalog", "ward_availability", "insurance_cashless"]:
            return "tools_node" # billing agent
            
        # Default fallback
        return "tools_node"
