import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import text
from config.settings import settings
from src.db.session import SessionLocal
from src.utils.logger import custom_logger as logger


TABLES = [
    "DEPARTMENTS",
    "DOCTORS",
    "DOCTOR_SCHEDULES",
    "PATIENTS",
    "APPOINTMENTS",
    "CALL_SESSIONS",
    "CONVERSATION_MESSAGES",
    "TOOL_CALL_AUDIT",
    "AUDIT_LOGS",
    "BILLING_CATALOG",
    "PHARMACY_INVENTORY",
    "INSURANCE_PROVIDERS",
    "LAB_REPORTS_METADATA",
    "USER_PREFERENCES",
    "DOCUMENTS",
    "WARD_MANAGEMENT",
    "ADMIN_USERS",
]


def check_database():
    logger.info(f"Checking database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
        logger.success("Database connection OK.")

        for table in TABLES:
            result = session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = result.scalar_one()
            logger.info(f"{table}: {count} rows")


if __name__ == "__main__":
    check_database()

