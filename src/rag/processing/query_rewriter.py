"""
query_rewriter.py
-----------------
Enterprise Query Rewriter & Intent Classifier for Conversational RAG.
Transforms conversational/ambiguous voice speech into dense, keyword-rich queries
with explicit department and category metadata filters before RAG retrieval.
"""

import re

from src.utils.logger import custom_logger as logger

# Department synonym dictionary for accurate metadata extraction
DEPARTMENT_MAPPINGS: dict[str, str] = {
    "heart": "cardiology",
    "cardio": "cardiology",
    "cardiac": "cardiology",
    "angioplasty": "cardiology",
    "brain": "neurology",
    "neuro": "neurology",
    "stroke": "neurology",
    "spine": "neurology",
    "paralysis": "neurology",
    "bone": "orthopedics",
    "ortho": "orthopedics",
    "joint": "orthopedics",
    "knee": "orthopedics",
    "fracture": "orthopedics",
    "child": "pediatrics",
    "baby": "pediatrics",
    "pediatric": "pediatrics",
    "nicu": "pediatrics",
    "infant": "pediatrics",
    "pregnancy": "gynecology & obstetrics",
    "maternity": "gynecology & obstetrics",
    "delivery": "gynecology & obstetrics",
    "gynae": "gynecology & obstetrics",
    "skin": "dermatology",
    "hair": "dermatology",
    "acne": "dermatology",
    "allergy": "dermatology",
    "ear": "ent",
    "nose": "ent",
    "throat": "ent",
    "sinus": "ent",
    "stomach": "gastroenterology",
    "gastro": "gastroenterology",
    "liver": "gastroenterology",
    "endoscopy": "gastroenterology",
    "cancer": "oncology",
    "tumor": "oncology",
    "chemo": "oncology",
    "lungs": "pulmonology",
    "chest": "pulmonology",
    "asthma": "pulmonology",
    "copd": "pulmonology",
    "kidney": "nephrology",
    "dialysis": "nephrology",
    "renal": "nephrology",
    "fever": "general medicine",
    "sugar": "general medicine",
    "diabetes": "general medicine",
    "bp": "general medicine",
    "mri": "radiology",
    "ct scan": "radiology",
    "xray": "radiology",
    "ultrasound": "radiology",
    "emergency": "emergency medicine",
    "ambulance": "emergency medicine",
    "casualty": "emergency medicine",
    "physio": "physiotherapy",
    "rehab": "physiotherapy",
}

CATEGORY_KEYWORDS: dict[str, str] = {
    "bill": "billing",
    "charge": "billing",
    "cost": "billing",
    "price": "billing",
    "fee": "billing",
    "deposit": "billing",
    "refund": "billing",
    "insurance": "insurance",
    "tpa": "insurance",
    "cashless": "insurance",
    "ayushman": "insurance",
    "claim": "insurance",
    "timing": "general",
    "hours": "general",
    "visiting": "general",
    "location": "general",
    "address": "general",
    "parking": "general",
    "pharmacy": "pharmacy",
    "medicine": "pharmacy",
    "drug": "pharmacy",
    "prescription": "pharmacy",
}


class QueryUnderstandingEngine:
    """
    Analyzes, rewrites, and enriches patient voice queries before passing to Hybrid RAG.
    Performs:
      1. Pronoun and conversational filler resolution.
      2. Metadata filter extraction (Department, Category).
      3. Medical synonym expansion.
    """

    @staticmethod
    def process_query(raw_query: str, last_context: str | None = None) -> tuple[str, str | None, str | None]:
        """
        Takes raw spoken query and returns:
          (rewritten_query, department_filter, category_filter)
        """
        if not raw_query or not raw_query.strip():
            return "", None, None

        cleaned = raw_query.strip().lower()
        # Remove conversational speech artifacts
        cleaned = re.sub(r'\b(um|uh|please tell me|can you tell me|i want to know|batao|kya hai)\b', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 1. Detect Category Filter
        detected_category: str | None = None
        for kw, cat in CATEGORY_KEYWORDS.items():
            if kw in cleaned:
                detected_category = cat
                break

        # 2. Detect Department Filter
        detected_department: str | None = None
        for kw, dept in DEPARTMENT_MAPPINGS.items():
            if kw in cleaned:
                detected_department = dept
                break

        # 3. Query Rewriting & Expansion
        rewritten_query = cleaned

        # Common spoken query expansions
        if "visiting" in cleaned or "milne ka time" in cleaned:
            rewritten_query = "visiting hours guidelines for general wards and ICU"
            detected_category = "general"
        elif "cashless" in cleaned or "star health" in cleaned or "ayushman" in cleaned:
            rewritten_query = f"cashless health insurance TPA process {cleaned}"
            detected_category = "insurance"
        elif "doctor" in cleaned or "dr" in cleaned or "opd" in cleaned:
            if detected_department:
                rewritten_query = f"{detected_department} specialist doctor OPD timings and schedule"
        elif "emergency" in cleaned or "ambulance" in cleaned or "casualty" in cleaned:
            rewritten_query = "24x7 emergency helpline ambulance admission triage protocols"
            detected_department = "emergency medicine"

        logger.debug(
            f"Query Understanding: Raw='{raw_query}' -> Rewritten='{rewritten_query}' "
            f"(Category={detected_category}, Dept={detected_department})"
        )

        return (rewritten_query if rewritten_query else raw_query, detected_department, detected_category)
