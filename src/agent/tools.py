import random
from src.rag.query.engine import RAGQueryEngine
from src.utils.logger import custom_logger as logger

# Initialize RAG Engine
rag_engine = RAGQueryEngine()

def search_hospital_knowledge(query: str):
    logger.info(f"Tool Call: Searching Knowledge for '{query}'")
    return rag_engine.query(query)

def book_appointment(doctor_name: str, date_time: str):
    logger.info(f"Tool Call: Booking for {doctor_name}")
    return f"SUCCESS: Appointment fixed with {doctor_name} for {date_time}."

def check_emergency_availability(service_type: str):
    logger.info(f"Tool Call: Checking availability for {service_type}")
    return f"Yes, 3 units of {service_type} are available at City Care Hospital."

TOOL_MAP = {
    "search_hospital_knowledge": search_hospital_knowledge,
    "book_appointment": book_appointment,
    "check_emergency_availability": check_emergency_availability
}
