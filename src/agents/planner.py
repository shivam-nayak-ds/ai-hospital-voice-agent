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
import re
import asyncio
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
            from src.agents.ananya_agent import get_groq_client, get_gemini_client
            groq_client = get_groq_client()
            gemini_client = get_gemini_client()
            
            from src.agents.prompts import SYSTEM_ROUTER_PROMPT
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = SYSTEM_ROUTER_PROMPT.format(current_date=current_date)
            
            from src.utils.message_helper import get_message_content
            last_user_message = get_message_content(messages[-1])
            intent = "chitchat"
            entities = {}
            heuristic_matched = False
            
            # 0. Heuristic Rules FIRST (instant — skips LLM for common patterns)
            text_lower = last_user_message.lower()
            if any(w in text_lower for w in ["book", "appointment", "reserve", "slot"]):
                intent = "book_appointment"
                heuristic_matched = True
            elif any(w in text_lower for w in ["doctor", "physician", "practitioner", "timings of dr", "schedule of dr"]):
                intent = "doctor_search"
                heuristic_matched = True
            elif any(w in text_lower for w in ["report", "lab", "test status"]):
                intent = "lab_report_status"
                heuristic_matched = True
            elif any(w in text_lower for w in ["emergency", "chest pain", "bleeding"]):
                intent = "emergency"
                heuristic_matched = True
            elif any(w in text_lower for w in ["price", "cost", "billing", "charges"]):
                intent = "billing_catalog"
                heuristic_matched = True
            elif any(w in text_lower for w in ["tell me about", "department", "departments", "specialty", "speciality", "specialties", "address", "location", "where is", "direction", "timing", "timings", "hours", "open", "visiting", "policy", "faq", "question"]):
                intent = "faq"
                heuristic_matched = True
            
            if heuristic_matched:
                log.info(f"Heuristic matched intent: '{intent}' (skipping LLM)")
            
            # 1. LLM Classification only if heuristic didn't match
            _LLM_TIMEOUT = 5  # NLU must be fast — 5s hard ceiling
            groq_success = False
            
            if not heuristic_matched and groq_client:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            groq_client.chat.completions.create,
                            model=settings.GROQ_MODEL,
                            messages=[
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": last_user_message}
                            ],
                            response_format={"type": "json_object"}
                        ),
                        timeout=_LLM_TIMEOUT
                    )
                    data = json.loads(response.choices[0].message.content)
                    intent = data.get("intent", "chitchat")
                    entities = data.get("extracted_entities", {})
                    log.info(f"Groq intent classified as: '{intent}'")
                    groq_success = True
                except (asyncio.TimeoutError, Exception) as e:
                    log.warning(f"Groq NLU extraction failed ({type(e).__name__}): {e}")
                    
            # 2. Gemini Fallback (only if heuristic didn't match AND Groq failed)
            if not heuristic_matched and not groq_success and gemini_client:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            gemini_client.chat.completions.create,
                            model=settings.GEMINI_MODEL,
                            messages=[
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": last_user_message}
                            ],
                            response_format={"type": "json_object"}
                        ),
                        timeout=_LLM_TIMEOUT
                    )
                    data = json.loads(response.choices[0].message.content)
                    intent = data.get("intent", "chitchat")
                    entities = data.get("extracted_entities", {})
                    log.info(f"Gemini fallback intent classified as: '{intent}'")
                except (asyncio.TimeoutError, Exception) as e:
                    log.warning(f"Gemini NLU extraction failed ({type(e).__name__}): {e}")
                    
            # 3. Post-LLM heuristic refinement (only if LLM returned chitchat)
            if not heuristic_matched and intent == "chitchat":
                if any(w in text_lower for w in ["book", "appointment", "reserve", "slot"]):
                    intent = "book_appointment"
                elif any(w in text_lower for w in ["doctor", "physician", "practitioner", "timings of dr", "schedule of dr"]):
                    intent = "doctor_search"
                elif any(w in text_lower for w in ["report", "lab", "test status"]):
                    intent = "lab_report_status"
                elif any(w in text_lower for w in ["emergency", "chest pain", "bleeding"]):
                    intent = "emergency"
                elif any(w in text_lower for w in ["price", "cost", "billing", "charges"]):
                    intent = "billing_catalog"
                elif any(w in text_lower for w in ["tell me about", "department", "departments", "specialty", "speciality", "specialties", "address", "location", "where is", "direction", "timing", "timings", "hours", "open", "visiting", "policy", "faq", "question"]):
                    intent = "faq"

            # 4. Extract 10-digit phone number if missing from LLM extraction
            if not entities:
                entities = {}
            if not entities.get("patient_phone"):
                phone_match = re.search(r"\b\d{10}\b", last_user_message)
                if phone_match:
                    entities["patient_phone"] = phone_match.group(0)

            # 5. Preserve active intent during multi-turn slot filling / OTP verification
            intent_requirements = {
                "book_appointment": ["doctor_name", "appointment_date", "appointment_time", "patient_phone"],
                "check_slot": ["doctor_name", "appointment_date", "appointment_time"],
                "cancel_appointment": ["appointment_id"],
                "lab_report_status": ["patient_phone"],
                "billing_catalog": ["specialization"],
                "insurance_cashless": ["specialization"]
            }

            prev_intent = state.get("current_intent")
            is_otp_verified = state.get("is_otp_verified", False)
            
            if prev_intent in intent_requirements:
                is_secure = prev_intent in ["book_appointment", "cancel_appointment", "lab_report_status"]
                needs_otp = is_secure and not is_otp_verified
                
                # Check if any required slots are still missing
                req_slots = intent_requirements[prev_intent]
                missing_slots = any(state.get(slot) is None and entities.get(slot) is None for slot in req_slots)
                
                if intent == "chitchat" or needs_otp or missing_slots:
                    log.info(f"NLU Flow: Preserving active intent '{prev_intent}' (needs_otp={needs_otp}, missing_slots={missing_slots})")
                    intent = prev_intent
                    
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
            
        if intent == "faq":
            return "rag_node"
            
        if intent in ["billing_catalog", "ward_availability", "insurance_cashless"]:
            return "tools_node" # billing agent
            
        # Default fallback
        return "tools_node"
