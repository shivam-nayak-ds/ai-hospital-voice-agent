from src.utils.logger import custom_logger as logger

# ─── Emergency Contacts ──────────────────────────────────────────────────────
EMERGENCY_CONTACTS = {
    "ambulance": "108",
    "hospital_emergency": "+91-9999999999",   # Updated placeholder with a mock valid sequence
    "icu_helpdesk": "Extension 999",
    "police": "100",
    "fire": "101",
    "women_helpline": "1091",
}

# ─── Keyword-Specific Responses ───────────────────────────────────────────────
KEYWORD_RESPONSES = {
    "chest pain": (
        "Chest pain can indicate a heart attack. Call 108 immediately. "
        "Ask the patient to sit down, loosen clothing, and avoid exertion. "
        "Do not give food or water. Our Cardiology Emergency team is available 24/7."
    ),
    "accident": (
        "For accident victims, call 108 immediately. Do not move the patient unnecessarily. "
        "Apply pressure to visible bleeding wounds with a clean cloth. "
        "Our trauma team at Lifeline ER is on standby 24/7."
    ),
    "unconscious": (
        "If the patient is unconscious, check for breathing. "
        "Call 108 now. Lay the patient on their side if breathing, "
        "or begin CPR if trained. Our ER team can guide you over the phone."
    ),
    "bleeding": (
        "Apply firm pressure to the wound with a clean cloth. "
        "Raise the injured part above heart level if possible. "
        "Call 108 or come directly to our ER. Surgical team is available 24/7."
    ),
    "breathing": (
        "Breathing difficulty can be serious. Call 108 immediately. "
        "Keep the patient seated upright. Loosen any tight clothing around neck and chest. "
        "Our Pulmonology Emergency is available at Lifeline Multi-Speciality Hospital."
    ),
    "stroke": (
        "Possible stroke detected. Call 108 immediately. "
        "Note the time symptoms started — this is critical for treatment. "
        "Do not give food or water. Keep the patient calm and still. "
        "Our Neurology Emergency team is available 24/7."
    ),
}

def handle_emergency(user_query: str) -> str:
    """
    Returns instant emergency guidance based on the situation.
    Zero-latency — no DB or RAG calls.
    """
    query_lower = user_query.lower()

    # Match emergency keywords only if they appear as word boundaries to reduce false positives
    import re
    for keyword, response in KEYWORD_RESPONSES.items():
        if re.search(rf"\b{keyword}\b", query_lower):
            logger.warning(f"Emergency Tool: Keyword '{keyword}' detected.")
            return response

    # Generic fallback
    logger.warning(f"Emergency Tool: Generic emergency for: '{user_query}'")
    return (
        "This sounds like a medical emergency. Please:\n\n"
        "1. Call ambulance at 108 immediately.\n"
        "2. Do NOT move the patient if they had a fall or accident.\n"
        "3. Our Emergency Room is open 24/7 — go to the gate and say EMERGENCY.\n"
        f"4. Hospital Emergency Helpline: {EMERGENCY_CONTACTS['hospital_emergency']}\n"
        f"5. ICU Helpdesk: {EMERGENCY_CONTACTS['icu_helpdesk']}"
    )

def get_emergency_contacts() -> str:
    """Returns all emergency contact numbers."""
    labels = {
        "ambulance": "Ambulance (National)",
        "hospital_emergency": "Hospital Emergency Helpline",
        "icu_helpdesk": "ICU Helpdesk",
        "police": "Police",
        "fire": "Fire Department",
        "women_helpline": "Women's Helpline",
    }
    lines = ["Emergency Contacts at Lifeline Multi-Speciality Hospital:\n"]
    for key, label in labels.items():
        lines.append(f"  - {label}: {EMERGENCY_CONTACTS[key]}")
    return "\n".join(lines)
