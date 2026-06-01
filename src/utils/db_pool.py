"""
PostgreSQL Connection Management & DB Utils
=======================================================
Problem Solved:
  - Legacy code used mysql-connector connection pooling on a PostgreSQL database.
  - Case-sensitivity issues in PostgreSQL for uppercase table names (needs double quotes).
  - SQL dialect mismatches.

Solution:
  - Reuses SQLAlchemy Engine connection pool (built-in QueuePool).
  - Uses double-quoted uppercase table/column names for PostgreSQL.
  - Implements atomic bookings using SQLAlchemy transaction context.
  - Query result caching for read-heavy calls via Redis.
"""

import os
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from src.utils.logger import custom_logger as logger
from sqlalchemy import text
from src.db.session import engine
from config.settings import settings

load_dotenv()

def get_db_connection():
    """
    Get an SQLAlchemy connection from the engine pool.
    Usage: with get_db_connection() as conn: ...
    """
    return engine.connect()

# ─── Query Result Cache ──────────────────────────────────────────────────────
try:
    import redis
    _redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=1,
    )
    _redis.ping()
    DB_CACHE_AVAILABLE = True
    logger.success(" DB Query Cache: Redis ONLINE")
except Exception:
    DB_CACHE_AVAILABLE = False

DB_CACHE_PREFIX = "asha:db:"
DB_CACHE_TTL = 180      # 3 minutes for doctor/billing lists


def _db_cache_get(key: str) -> Optional[str]:
    if not DB_CACHE_AVAILABLE:
        return None
    try:
        return _redis.get(f"{DB_CACHE_PREFIX}{key}")
    except Exception:
        return None


def _db_cache_set(key: str, value: str, ttl: int = DB_CACHE_TTL):
    if not DB_CACHE_AVAILABLE:
        return
    try:
        _redis.set(f"{DB_CACHE_PREFIX}{key}", value, ex=ttl)
    except Exception:
        pass


def _db_cache_invalidate(pattern: str):
    """Invalidate cache entries matching pattern (call after writes)."""
    if not DB_CACHE_AVAILABLE:
        return
    try:
        keys = _redis.keys(f"{DB_CACHE_PREFIX}{pattern}*")
        if keys:
            _redis.delete(*keys)
    except Exception:
        pass


# ─── Appointment Conflict Detection ─────────────────────────────────────────

def check_appointment_conflict(doctor_name: str, appointment_time: str) -> Dict[str, Any]:
    """
    Check if a doctor already has an appointment at the requested time.
    Returns: {"conflict": bool, "existing_patient": str or None}
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """SELECT "PATIENT_NAME" FROM "APPOINTMENTS"
                       WHERE "DOCTOR_NAME" ILIKE :doctor_name
                       AND "APPOINTMENT_TIME" = :appointment_time
                       AND "APPOINTMENT_DATE" = CURRENT_DATE
                       LIMIT 1"""
                ),
                {"doctor_name": f"%{doctor_name}%", "appointment_time": appointment_time}
            )
            existing = result.mappings().first()
            if existing:
                return {"conflict": True, "existing_patient": existing["PATIENT_NAME"]}
            return {"conflict": False, "existing_patient": None}
    except Exception as e:
        logger.warning(f"Conflict check failed: {e}")
        return {"conflict": False, "existing_patient": None}


def get_doctor_available_slots(doctor_name: str) -> str:
    """
    Returns available appointment slots for a doctor today.
    Uses cached result to avoid repeated DB hits.
    """
    cache_key = f"slots:{doctor_name.lower().replace(' ', '_')}"
    cached = _db_cache_get(cache_key)
    if cached:
        logger.info(f"[DB Cache HIT] doctor slots for {doctor_name}")
        return cached

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """SELECT "APPOINTMENT_TIME" FROM "APPOINTMENTS"
                       WHERE "DOCTOR_NAME" ILIKE :doctor_name
                       AND "APPOINTMENT_DATE" = CURRENT_DATE"""
                ),
                {"doctor_name": f"%{doctor_name}%"}
            )
            booked = {row["APPOINTMENT_TIME"] for row in result.mappings().all()}

        # Standard clinic slots (9 AM - 5 PM, hourly)
        all_slots = [
            "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
            "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM",
        ]
        available = [s for s in all_slots if s not in booked]

        if not available:
            result_str = f"Dr. {doctor_name} is fully booked for today. Please try tomorrow."
        else:
            result_str = f"Available slots for Dr. {doctor_name} today: {', '.join(available[:4])}."

        _db_cache_set(cache_key, result_str, ttl=60)  # Cache for 1 min
        return result_str

    except Exception as e:
        logger.error(f"Slot check error: {e}")
        return f"Please call our front desk to check Dr. {doctor_name}'s availability."


# ─── Cached Doctor Search ────────────────────────────────────────────────────

def search_doctors_cached(specialization: str = None, name: str = None) -> str:
    """
    Doctor search with Redis caching.
    """
    cache_key = f"doctors:{specialization or ''}:{name or ''}"
    cached = _db_cache_get(cache_key)
    if cached:
        logger.info("[DB Cache HIT] doctor search")
        return cached

    try:
        query_str = 'SELECT "NAME", "SPECIALIZATION", "STATUS" FROM "DOCTORS" WHERE 1=1'
        params = {}
        if specialization:
            query_str += ' AND "SPECIALIZATION" ILIKE :specialization'
            params["specialization"] = f"%{specialization}%"
        if name:
            query_str += ' AND "NAME" ILIKE :name'
            params["name"] = f"%{name}%"
        query_str += ' ORDER BY "STATUS" DESC LIMIT 10'

        with engine.connect() as conn:
            result = conn.execute(text(query_str), params)
            results = result.mappings().all()

        if not results:
            result_str = "I apologize, we don't have a doctor available for that specialization right now."
        else:
            res_str = "We have the following doctors available: "
            for d in results:
                res_str += f"{d['NAME']} ({d['SPECIALIZATION']}) - {d['STATUS']}. "
            result_str = res_str.strip()

        _db_cache_set(cache_key, result_str)
        return result_str

    except Exception as e:
        logger.error(f"Doctor Search Error: {e}")
        return "Database is temporarily unavailable. Please call our front desk."


def book_appointment_safe(doctor_name: str, patient_name: str, time: str) -> str:
    """
    Enterprise Booking:
    1. Single Transaction with Row-Level Locking (SELECT FOR UPDATE)
    2. Atomic Conflict Check + Insert
    3. Prevents Double-Booking across concurrent calls
    """
    try:
        with engine.begin() as conn:
            # 1. Lock the doctor's record to prevent concurrent bookings
            doctor_res = conn.execute(
                text('SELECT "NAME" FROM "DOCTORS" WHERE "NAME" ILIKE :doctor_name FOR UPDATE'),
                {"doctor_name": f"%{doctor_name}%"}
            )
            doctor = doctor_res.mappings().first()
            if not doctor:
                return f"Dr. {doctor_name} is not found in our records."
            
            real_doctor_name = doctor["NAME"]

            # 2. Check for conflict within the locked transaction
            conflict_res = conn.execute(
                text(
                    """SELECT "PATIENT_NAME" FROM "APPOINTMENTS"
                       WHERE "DOCTOR_NAME" = :doctor_name
                       AND "APPOINTMENT_TIME" = :time
                       AND "APPOINTMENT_DATE" = CURRENT_DATE
                       FOR UPDATE"""
                ),
                {"doctor_name": real_doctor_name, "time": time}
            )
            if conflict_res.mappings().first():
                slots_msg = get_doctor_available_slots(real_doctor_name)
                return (
                    f"I'm sorry, Dr. {real_doctor_name} was just booked at {time}. "
                    f"{slots_msg} Would you like to pick another slot?"
                )

            # 3. Perform the Insert
            conn.execute(
                text(
                    """INSERT INTO "APPOINTMENTS" ("PATIENT_NAME", "DOCTOR_NAME", "APPOINTMENT_TIME", "APPOINTMENT_DATE")
                       VALUES (:patient_name, :doctor_name, :time, CURRENT_DATE)"""
                ),
                {"patient_name": patient_name, "doctor_name": real_doctor_name, "time": time}
            )

        # Invalidate slots cache
        _db_cache_invalidate(f"slots:{real_doctor_name.lower().replace(' ', '_')}")

        return (
            f"Your appointment with {real_doctor_name} has been confirmed at {time}. "
            f"We look forward to seeing you, {patient_name}."
        )

    except Exception as e:
        logger.error(f"Atomic Booking Error: {e}")
        return "The booking system is currently busy. Please try again in a moment."


def log_audit_action(action_type: str, user_id: str, details: str):
    """
    Enterprise Audit Logging: Every sensitive action is recorded in the DB.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text('INSERT INTO "AUDIT_LOGS" ("ACTION_TYPE", "USER_ID", "ACTION_DETAILS") VALUES (:action_type, :user_id, :details)'),
                {"action_type": action_type, "user_id": user_id, "details": details}
            )
    except Exception as e:
        logger.error(f"Audit Log Error: {e}")


def check_insurance_acceptance(provider_name: str) -> str:
    """Checks if a specific insurance provider is accepted for cashless treatment."""
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text('SELECT "NAME", "CASHLESS_AVAILABLE", "HELPLINE" FROM "INSURANCE_PROVIDERS" WHERE "NAME" ILIKE :provider_name'),
                {"provider_name": f"%{provider_name}%"}
            )
            result = res.mappings().first()
            if not result:
                return f"I couldn't find {provider_name} in our accepted insurance list. Please contact our billing desk for reimbursement options."
            
            status = "accepted for cashless treatment" if result['CASHLESS_AVAILABLE'] else "accepted only for reimbursement"
            return f"Yes, {result['NAME']} is {status}. Their helpline is {result['HELPLINE']}."
    except Exception as e:
        logger.error(f"Insurance Query Error: {e}")
        return "Insurance information is temporarily unavailable."


def get_ward_status() -> str:
    """Returns real-time bed availability in various hospital wards."""
    try:
        with engine.connect() as conn:
            res = conn.execute(text('SELECT "WARD_TYPE", "TOTAL_BEDS", "OCCUPIED_BEDS", "PRICE_PER_DAY" FROM "WARD_MANAGEMENT"'))
            results = res.mappings().all()
        
        if not results:
            return "Ward information is currently unavailable."
        
        resp = "Current Ward Availability: "
        for r in results:
            avail = r['TOTAL_BEDS'] - r['OCCUPIED_BEDS']
            resp += f"{r['WARD_TYPE']}: {avail} beds available (Rate: ₹{r['PRICE_PER_DAY']}/day). "
        return resp.strip()
    except Exception as e:
        logger.error(f"Ward Query Error: {e}")
        return "Bed availability information is temporarily unavailable."
