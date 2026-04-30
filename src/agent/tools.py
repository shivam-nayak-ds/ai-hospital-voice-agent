import mysql.connector
import os
import random
from dotenv import load_dotenv
from src.rag.query.engine import RAGQueryEngine
from src.utils.logger import custom_logger as logger

# Load credentials
load_dotenv()

# Initialize RAG Engine
try:
    rag_engine = RAGQueryEngine()
except Exception as e:
    logger.error(f"RAG Engine Initialization Failed: {e}")
    rag_engine = None

def search_hospital_knowledge(query: str):
    """Knowledge base search (ChromaDB)"""
    try:
        if not rag_engine: return "Knowledge base is offline."
        return rag_engine.query(query)
    except Exception as e:
        logger.error(f"RAG Error: {e}")
        return "I am unable to access hospital info right now."

def search_doctors(specialization: str = None, name: str = None):
    """MySQL se doctor aur unka STATUS nikalne ke liye"""
    logger.info(f"Tool Call: Searching Doctors (Spec: {specialization}, Name: {name})")
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=os.getenv("DB_PASSWORD"),
            database="Ai_hospital_agent"
        )
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT NAME, SPECIALIZATION, CONSULTATION_FEE, MAX_SLOTS_PER_DAY FROM DOCTORS WHERE 1=1"
        params = []
        if specialization:
            query += " AND SPECIALIZATION LIKE %s"
            params.append(f"%{specialization}%")
        if name:
            query += " AND NAME LIKE %s"
            params.append(f"%{name}%")
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return "Ji, mujhe system mein matching details ke saath koi doctor nahi mile. Kya main kisi aur specialty ya doctor ka naam check karoon?"
            
        res_str = "Ji, mujhe ye doctors mile hain: "
        for d in results:
            # 🔥 DYNAMIC SLOT CALCULATION
            cursor.execute("SELECT COUNT(*) as count FROM APPOINTMENTS WHERE DOCTOR_NAME = %s AND APPOINTMENT_DATE = CURRENT_DATE", (d['NAME'],))
            booked_today = cursor.fetchone()['count']
            remaining_slots = max(0, d['MAX_SLOTS_PER_DAY'] - booked_today)
            
            status = "Available" if remaining_slots > 0 else "Fully Booked for Today"
            
            res_str += f"{d['NAME']} ({d['SPECIALIZATION']}). Status: {status}. Aaj {remaining_slots} slots baaki hain. "
        return res_str

    except Exception as e:
        logger.error(f"SQL Search Error: {e}")
        return "Technical issues with doctor database."
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def book_appointment(doctor_name: str, patient_name: str, time: str):
    """Appointment save karne aur status check karne ke liye"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=os.getenv("DB_PASSWORD"),
            database="Ai_hospital_agent"
        )
        cursor = connection.cursor(dictionary=True)

        # 🔒 START TRANSACTION (Enterprise Race-Condition Fix)
        connection.start_transaction()

        # 1. Check if doctor exists using LIKE to handle partial names
        # 'FOR UPDATE' locks this specific doctor's row so no other agent can book them simultaneously!
        cursor.execute("SELECT NAME, STATUS, MAX_SLOTS_PER_DAY FROM DOCTORS WHERE NAME LIKE %s LIMIT 1 FOR UPDATE", (f"%{doctor_name}%",))
        doctor = cursor.fetchone()

        if not doctor:
            return f"Maaf kijiye, {doctor_name} system mein nahi mile. Kya aap doctor ka pura naam aur specialty bata sakte hain?"

        real_doctor_name = doctor['NAME']

        if doctor['STATUS'] != 'Available':
            return f"Maaf kijiye, {real_doctor_name} abhi {doctor['STATUS']} hain. Kya main kisi aur time ya doctor ke liye check karu?"

        # 🔥 SLOT AUTOMATION: Check max slots limit
        cursor.execute("SELECT COUNT(*) as count FROM APPOINTMENTS WHERE DOCTOR_NAME = %s AND APPOINTMENT_DATE = CURRENT_DATE", (real_doctor_name,))
        booked_today = cursor.fetchone()['count']
        
        max_slots = doctor['MAX_SLOTS_PER_DAY']

        if booked_today >= max_slots:
            return f"Maaf kijiye, {real_doctor_name} ki aaj ki saari ({max_slots}) appointments full ho chuki hain. Kya main kal ke liye check karu?"

        # 2. Insert into APPOINTMENTS table
        insert_query = "INSERT INTO APPOINTMENTS (PATIENT_NAME, DOCTOR_NAME, APPOINTMENT_TIME, APPOINTMENT_DATE) VALUES (%s, %s, %s, CURRENT_DATE)"
        cursor.execute(insert_query, (patient_name, real_doctor_name, time))
        connection.commit()

        # 3. Simulate Notification
        print(f"\n--- [NOTIFICATION SENT] ---")
        print(f"Dr. {real_doctor_name}: New booking from {patient_name} at {time}.")
        
        return f"Confirm! {patient_name}, aapki appointment {real_doctor_name} ke saath {time} baje fix ho gayi hai."

    except Exception as e:
        logger.error(f"Booking Error: {e}")
        return "Sorry, main appointment book nahi kar paa rahi hoon."
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def request_ambulance(address: str):
    """Emergency ambulance dispatch logic"""
    try:
        is_available = random.choice([True, True, True, False]) # 75% availability
        if not is_available:
            return "Maaf kijiye, abhi humari saari ambulances busy hain. Please turant 102 par call karein."

        logger.warning(f"EMERGENCY: Ambulance dispatched to {address}")
        return f"Maine check kiya hai, ek ambulance free hai aur use {address} ke liye nikal diya gaya hai. Wo 15 min mein pahunch jayegi."
    except Exception as e:
        logger.error(f"Ambulance Error: {e}")
        return "Error in dispatching ambulance. Call 102."

# Agent Tool Map
TOOL_MAP = {
    "search_hospital_knowledge": search_hospital_knowledge,
    "search_doctors": search_doctors,
    "book_appointment": book_appointment,
    "request_ambulance": request_ambulance
}
