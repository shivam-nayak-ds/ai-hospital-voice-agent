"""
guardrails.py
-------------
Implements pre-execution and post-execution guardrails for safety and policy compliance:
1. Input Sanitization: Detects and rejects prompt injection attempts.
2. Output Compliance: Blocks clinical suggestions, medical diagnosis, or medicine prescriptions,
   routing the caller to standard clinical care instead.
"""

import re
from typing import Dict, Any, Tuple
from src.utils.logger import custom_logger as logger

# Standard compliance warning when medical boundaries are breached
REFUSAL_MESSAGE = (
    "I am an AI assistant and cannot provide medical diagnoses or prescribe medicines. "
    "Please consult a qualified healthcare professional or visit our emergency department "
    "for clinical assistance."
)

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?prior\s+instructions",
    r"you\s+are\s+now\s+a\s+doctor",
    r"system\s+override",
    r"bypass\s+safety",
    r"disregard\s+instructions"
]

CLINICAL_KEYWORDS = [
    r"\bdiagnose\b",
    r"\bprescription\b",
    r"\bprescribe\b",
    r"\btablets\b",
    r"\bmedicine\b",
    r"\bmedication\b",
    r"\bcure\b",
    r"\bdose\b",
    r"\bdosage\b",
    r"\bantibiotic\b",
    r"\bparacetamol\b",
    r"\bibuprofen\b"
]

# Contexts where clinical keywords are SAFE (informational, not prescriptive)
# E.g. "The hospital pharmacy stocks all prescribed medicines" is OK
# E.g. "Take paracetamol 500mg twice daily" is NOT OK
_SAFE_CONTEXT_PATTERNS = [
    r"(?:pharmacy|stocks?|stores?|available|carries?|provides?|offers?|department|ward|facility|equipped)",
    r"(?:please consult|consult a|consult your|visit our|contact a|see a doctor|see your)",
    r"(?:cannot provide|cannot prescribe|cannot diagnose|do not provide)",
    r"(?:hospital|clinic|centre|center|helpdesk|extension|front desk)",
]

class AshaGuardrails:
    """
    Enforces HIPAA-compliant boundary checks and conversation safety.
    """
    @staticmethod
    def inspect_input(user_query: str) -> Tuple[bool, str]:
        """
        Scans incoming transcripts for potential prompt injection attempts.
        Returns:
            (is_safe, filtered_query_or_error_msg)
        """
        query_clean = user_query.strip()
        query_lower = query_clean.lower()
        
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, query_lower):
                logger.warning(f"Guardrail Flagged: Potential prompt injection attempt detected in query: '{user_query}'")
                return False, "I cannot process that request. Let's keep our conversation centered on hospital information and appointment scheduling."
                
        return True, query_clean

    @staticmethod
    def inspect_output(assistant_response: str) -> str:
        """
        Scans outgoing response for clinical claims, medical advice, or prescriptions.
        Uses context-aware checking to avoid false positives on informational responses.
        Returns:
            The safe response or the standard refusal message.
        """
        response_lower = assistant_response.lower()
        
        # First check if the response contains safe/informational context
        is_informational = any(
            re.search(pattern, response_lower) 
            for pattern in _SAFE_CONTEXT_PATTERNS
        )
        
        # If the response is clearly informational, allow it through
        if is_informational:
            return assistant_response
        
        for kw in CLINICAL_KEYWORDS:
            if re.search(kw, response_lower):
                logger.warning(f"Guardrail Flagged: Clinical keyword '{kw}' found in prescriptive context.")
                return REFUSAL_MESSAGE
                
        return assistant_response
