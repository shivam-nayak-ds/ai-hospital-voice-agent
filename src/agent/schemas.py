ASHA_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_hospital_knowledge",
            "description": "Use this tool to answer questions about hospital services, doctors, rules, ICU, and insurance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Use this tool to book a medical appointment. Requires doctor name and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Name of the doctor."},
                    "date_time": {"type": "string", "description": "Preferred date and time."}
                },
                "required": ["doctor_name", "date_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_emergency_availability",
            "description": "Checks if ICU beds or Emergency Doctors are available right now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_type": {"type": "string", "enum": ["ICU", "ER_Doctor"], "description": "The service to check."}
                },
                "required": ["service_type"]
            }
        }
    }
]
