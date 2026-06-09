"""
operations_agent.py
-------------------
Implements the specialist transaction agents (Booking, Billing, and Lab).
Manages multi-turn parameter gathering and executes database-backed tools.
Includes comprehensive try-except safety wrappers and production logs.
"""

from typing import Dict, Any
from src.utils.logger import custom_logger as logger

# Import database and transactional tools
from src.tools.appointment_tool import check_slot_availability, book_appointment, cancel_appointment
from src.tools.billing_tool import get_test_or_procedure_price, check_ward_rates, check_insurance_cashless
from src.tools.lab_tool import check_lab_report_status
from src.tools.doctor_tool import search_doctors_by_specialty, get_doctor_schedule

class AshaOperationsAgent:
    """
    Orchestrates Booking, Billing, and Lab database queries.
    Manages slot verification and handles missing details safely with exception recovery.
    """
    def __init__(self):
        logger.success("AshaOperationsAgent initialized.")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        session_id = state.get("session_id", "default")
        intent = state.get("current_intent")
        validation_errors = state.get("validation_errors", {})
        log = logger.bind(session_id=session_id)
        log.info(f"Operations Agent triggered for intent: '{intent}'")

        try:
            res = await self._execute_operation(state, intent, validation_errors, log)
            speech = res.get("speech_output", "")
            if speech:
                speech_lower = speech.lower()
                if "unavailable" in speech_lower or "failed" in speech_lower or "error" in speech_lower:
                    log.warning(f"Operations Agent: Tool failure detected: '{speech}'. Triggering no-hallucination guardrail.")
                    return {
                        "speech_output": "I am sorry, I am having trouble accessing our hospital records right now. Please try again shortly.",
                        "next_node": None
                    }
            return res
        except Exception as e:
            log.exception(f"Unhandled exception in Operations Agent: {e}")
            return {
                "speech_output": "I am having trouble accessing our hospital records right now. Please try again shortly.",
                "next_node": None
            }

    async def _execute_operation(
        self,
        state: Dict[str, Any],
        intent: str,
        validation_errors: Dict[str, str],
        log
    ) -> Dict[str, Any]:
        try:
            # ─── 1. Handling Validation Errors First ─────────────────────────────────
            if validation_errors:
                first_param = next(iter(validation_errors))
                error_msg = validation_errors[first_param]
                log.warning(f"Validation failure for parameter '{first_param}': {error_msg}")
                return {
                    "speech_output": error_msg,
                    "next_node": None
                }

            # ─── 2. Lab Report Status Flow ──────────────────────────────────────────
            if intent == "lab_report_status":
                phone = state.get("patient_phone")
                if not phone:
                    log.info("Lab status query missing phone details.")
                    return {
                        "speech_output": "Please tell me the ten digit mobile number associated with your lab sample.",
                        "next_node": None
                    }
                log.info(f"Checking lab status for phone: {phone}")
                result = await check_lab_report_status(phone)
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }

            # ─── 3. Billing & Ward Flow ─────────────────────────────────────────────
            elif intent == "billing_catalog":
                spec = state.get("specialization") or state.get("doctor_name")
                if not spec:
                    log.info("Billing catalog query missing test/procedure name.")
                    return {
                        "speech_output": "Which medical test or procedure price are you looking for?",
                        "next_node": None
                    }
                log.info(f"Checking pricing for: {spec}")
                result = await get_test_or_procedure_price(spec)
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }
                
            elif intent == "ward_availability":
                log.info("Fetching ward rates.")
                result = await check_ward_rates()
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }
                
            elif intent == "insurance_cashless":
                provider = state.get("specialization") or state.get("doctor_name")
                if not provider:
                    log.info("Insurance query missing company provider name.")
                    return {
                        "speech_output": "Could you please tell me the name of your insurance company?",
                        "next_node": None
                    }
                log.info(f"Checking insurance network for provider: {provider}")
                result = await check_insurance_cashless(provider)
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }

            # ─── 4. Doctor Search & Schedules ────────────────────────────────────────
            elif intent == "doctor_search":
                spec = state.get("specialization")
                doc = state.get("doctor_name")
                if doc:
                    log.info(f"Searching schedule for doctor: {doc}")
                    result = await get_doctor_schedule(doc)
                elif spec:
                    log.info(f"Searching doctors in department: {spec}")
                    result = await search_doctors_by_specialty(spec)
                else:
                    result = "Which department or doctor name are you searching for?"
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }
                
            elif intent == "doctor_schedule":
                doc = state.get("doctor_name")
                if not doc:
                    log.info("Doctor schedule lookup missing doctor name.")
                    return {
                        "speech_output": "Please specify the doctor's name to check their timings.",
                        "next_node": None
                    }
                log.info(f"Searching schedule for doctor: {doc}")
                result = await get_doctor_schedule(doc)
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }

            # ─── 5. Appointment Cancellation Flow ──────────────────────────────────
            elif intent == "cancel_appointment":
                appt_id = state.get("appointment_id")
                if not appt_id:
                    log.info("Cancellation missing appointment ID details.")
                    return {
                        "speech_output": "Please tell me the appointment ID you would like to cancel.",
                        "next_node": None
                    }
                log.info(f"Cancelling appointment ID: {appt_id}")
                result = await cancel_appointment(int(appt_id))
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }

            # ─── 6. Appointment Booking & Slot Check Flow ─────────────────────────
            elif intent in ["check_slot", "book_appointment"]:
                doc = state.get("doctor_name")
                appt_date = state.get("appointment_date")
                appt_time = state.get("appointment_time")
                phone = state.get("patient_phone")
                name = state.get("patient_name") or "Valued Patient"
                
                # Check parameters step-by-step
                if not doc:
                    log.info("Booking flow: missing doctor name.")
                    return {
                        "speech_output": "Which doctor would you like to schedule an appointment with?",
                        "next_node": None
                    }
                if not appt_date:
                    log.info(f"Booking flow: missing date for doctor '{doc}'.")
                    return {
                        "speech_output": f"For which date would you like to meet Dr. {doc}?",
                        "next_node": None
                    }
                if not appt_time:
                    log.info(f"Booking flow: missing slot time for doctor '{doc}' on '{appt_date}'.")
                    return {
                        "speech_output": f"At what time slot on {appt_date} would you like to see Dr. {doc}?",
                        "next_node": None
                    }
                    
                if intent == "check_slot":
                    log.info(f"Checking slot availability for Dr. {doc} on {appt_date} at {appt_time}")
                    result = await check_slot_availability(doc, appt_date, appt_time)
                    return {
                        "speech_output": result,
                        "next_node": "formatter_node"
                    }
                    
                # If booking, we also need patient phone
                if not phone:
                    log.info("Booking flow: missing phone verification.")
                    return {
                        "speech_output": "I will need your registered mobile number to confirm this booking.",
                        "next_node": None
                    }
                    
                log.info(f"Booking appointment for {name} with Dr. {doc} on {appt_date} at {appt_time}")
                result = await book_appointment(name, phone, doc, appt_date, appt_time)
                return {
                    "speech_output": result,
                    "next_node": "formatter_node"
                }

            # Fallback
            log.warning(f"Unrecognized intent '{intent}' passed to Operations Agent.")
            return {
                "speech_output": "I am not sure how to process that database transaction.",
                "next_node": None
            }

        except Exception as e:
            # Production Log: Record complete error details for debugging
            log.exception(f"Unhandled exception in Operations Agent: {e}")
            return {
                "speech_output": "I am having trouble accessing our hospital records right now. Please try again shortly.",
                "next_node": None
            }
