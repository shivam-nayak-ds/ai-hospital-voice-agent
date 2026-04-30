ASHA_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_hospital_knowledge",
            "description": "Search hospital policies, visitor hours, insurance coverage, and general FAQ from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query in plain English or Hinglish."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_doctors",
            "description": "Find doctors by specialization (e.g., Cardiologist) or Name. Use this to check if a doctor is available today.",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialization": {"type": "string", "description": "Medical specialty like Dentist, Dermatologist etc."},
                    "name": {"type": "string", "description": "Full or partial name of the doctor."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a doctor appointment. Only call this after confirming the doctor's name, patient's name, and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "The full name of the doctor."},
                    "patient_name": {"type": "string", "description": "The full name of the patient."},
                    "time": {"type": "string", "description": "The appointment time (e.g., 'Tomorrow 10 AM')."}
                },
                "required": ["doctor_name", "patient_name", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_ambulance",
            "description": "Emergency tool to dispatch an ambulance to a specific address. Call this immediately if an emergency is mentioned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "The pick-up address for the ambulance."}
                },
                "required": ["address"]
            }
        }
    }
]
