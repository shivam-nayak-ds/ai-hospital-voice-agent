from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Float, ForeignKey, Text, func, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from src.db.session import Base

# ─── 1. DEPARTMENTS TABLE ─────────────────────────────────────────────────────
class Department(Base):
    __tablename__ = "DEPARTMENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, unique=True, index=True)
    DESCRIPTION = Column("DESCRIPTION", String, nullable=True)
    LOCATION = Column("LOCATION", String, nullable=True)

    # Relationships
    doctors = relationship("Doctor", back_populates="department", cascade="all, delete-orphan")


# ─── 2. DOCTORS TABLE ─────────────────────────────────────────────────────────
class Doctor(Base):
    __tablename__ = "DOCTORS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, index=True)
    SPECIALIZATION = Column("SPECIALIZATION", String, nullable=False, index=True)
    QUALIFICATION = Column("QUALIFICATION", String, nullable=True)  # e.g., "MBBS, MD (Cardiology), DM (Interventional)"
    EXPERIENCE_YEARS = Column("EXPERIENCE_YEARS", Integer, nullable=True)  # e.g., 18
    CONSULTATION_FEE = Column("CONSULTATION_FEE", Integer, nullable=True)  # e.g., 1200
    LANGUAGES = Column("LANGUAGES", String, nullable=True)  # e.g., "Hindi, English, Marathi"
    STATUS = Column("STATUS", String, nullable=False, default="Active")  # e.g., Active, On Leave, Inactive
    EMAIL = Column("EMAIL", String, nullable=True)
    PHONE = Column("PHONE", String, nullable=True)
    DEPARTMENT_ID = Column("DEPARTMENT_ID", Integer, ForeignKey("DEPARTMENTS.ID"), nullable=False)

    # Composite index for fast doctor search queries (NAME + SPECIALIZATION)
    __table_args__ = (
        Index('idx_doctors_name_spec', 'NAME', 'SPECIALIZATION'),
    )

    # Relationships
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")


# ─── 3. DOCTOR SCHEDULES TABLE ────────────────────────────────────────────────
class DoctorSchedule(Base):
    __tablename__ = "DOCTOR_SCHEDULES"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    DAY_OF_WEEK = Column("DAY_OF_WEEK", String, nullable=False)  # e.g., Monday, Tuesday
    START_TIME = Column("START_TIME", String, nullable=False)    # e.g., "09:00 AM"
    END_TIME = Column("END_TIME", String, nullable=False)      # e.g., "05:00 PM"
    STATUS = Column("STATUS", String, nullable=False, default="Available")  # e.g., Available, Busy

    # Relationships
    doctor = relationship("Doctor", back_populates="schedules")


# ─── 4. PATIENTS TABLE ────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "PATIENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, index=True)
    AGE = Column("AGE", Integer, nullable=True)
    GENDER = Column("GENDER", String, nullable=True)
    PHONE = Column("PHONE", String, nullable=False, index=True)
    EMAIL = Column("EMAIL", String, nullable=True)
    ADDRESS = Column("ADDRESS", String, nullable=True)

    # Relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    lab_reports = relationship("LabReport", back_populates="patient", cascade="all, delete-orphan")


# ─── 5. APPOINTMENTS TABLE ────────────────────────────────────────────────────
class Appointment(Base):
    __tablename__ = "APPOINTMENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_NAME = Column("PATIENT_NAME", String, nullable=False)
    DOCTOR_NAME = Column("DOCTOR_NAME", String, nullable=False)
    APPOINTMENT_TIME = Column("APPOINTMENT_TIME", String, nullable=False)
    APPOINTMENT_DATE = Column("APPOINTMENT_DATE", Date, default=func.current_date(), nullable=False)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    STATUS = Column("STATUS", String, nullable=False, default="Confirmed")  # Confirmed, Cancelled

    # DB-level unique constraint to prevent double-booking same doctor at same time on same date
    __table_args__ = (
        UniqueConstraint('DOCTOR_ID', 'APPOINTMENT_TIME', 'APPOINTMENT_DATE', name='uq_doctor_slot'),
        Index('idx_appt_doctor_date', 'DOCTOR_ID', 'APPOINTMENT_DATE'),
    )

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


# ─── 6. BILLING CATALOG TABLE ──────────────────────────────────────────────────
class BillingCatalog(Base):
    __tablename__ = "BILLING_CATALOG"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    ITEM_NAME = Column("ITEM_NAME", String, nullable=False, index=True)
    CATEGORY = Column("CATEGORY", String, nullable=False)  # e.g., Consultation, Lab Test, Surgery, Ward
    PRICE = Column("PRICE", Integer, nullable=False)
    CODE = Column("CODE", String, nullable=False, unique=True, index=True)  # e.g., BILL_GEN_CONS


# ─── 7. INSURANCE PROVIDERS TABLE ──────────────────────────────────────────────
class InsuranceProvider(Base):
    __tablename__ = "INSURANCE_PROVIDERS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, unique=True, index=True)
    CASHLESS_AVAILABLE = Column("CASHLESS_AVAILABLE", Boolean, default=True, nullable=False)
    HELPLINE = Column("HELPLINE", String, nullable=True)


# ─── 8. WARD MANAGEMENT TABLE ──────────────────────────────────────────────────
class WardManagement(Base):
    __tablename__ = "WARD_MANAGEMENT"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    WARD_TYPE = Column("WARD_TYPE", String, nullable=False, unique=True, index=True)  # ICU, Deluxe, Private, Semi-Private, General
    TOTAL_BEDS = Column("TOTAL_BEDS", Integer, nullable=False)
    OCCUPIED_BEDS = Column("OCCUPIED_BEDS", Integer, nullable=False, default=0)
    PRICE_PER_DAY = Column("PRICE_PER_DAY", Integer, nullable=False)

    # DB-level constraint: occupied beds can never exceed total beds (prevents race condition overbooking)
    __table_args__ = (
        CheckConstraint('"OCCUPIED_BEDS" >= 0', name='chk_occupied_beds_positive'),
        CheckConstraint('"OCCUPIED_BEDS" <= "TOTAL_BEDS"', name='chk_occupied_beds_limit'),
    )


# ─── 9. LAB REPORTS TABLE ──────────────────────────────────────────────────────
class LabReport(Base):
    __tablename__ = "LAB_REPORTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    TEST_NAME = Column("TEST_NAME", String, nullable=False, index=True)  # e.g., CBC, Thyroid Profile
    RESULT = Column("RESULT", String, nullable=True)  # Normal, Hb: 10.5 (Low), etc.
    STATUS = Column("STATUS", String, nullable=False, default="Pending")  # Pending, Completed
    ORDERED_DATE = Column("ORDERED_DATE", Date, default=func.current_date(), nullable=False)
    REPORT_URL = Column("REPORT_URL", String, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="lab_reports")


# ─── 10. CONVERSATION LOGS TABLE ───────────────────────────────────────────────
class ConversationLog(Base):
    __tablename__ = "CONVERSATION_LOGS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    SESSION_ID = Column("SESSION_ID", String, nullable=False, index=True)
    ROLE = Column("ROLE", String, nullable=False)  # user, assistant, system
    CONTENT = Column("CONTENT", Text, nullable=False)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)


# ─── 11. AGENT EVENTS TABLE ────────────────────────────────────────────────────
class AgentEvent(Base):
    __tablename__ = "AGENT_EVENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    SESSION_ID = Column("SESSION_ID", String, nullable=False, index=True)
    EVENT_TYPE = Column("EVENT_TYPE", String, nullable=False, index=True)  # intent_route, exception, latency
    ROUTER_NAME = Column("ROUTER_NAME", String, nullable=True)
    EXECUTION_TIME_MS = Column("EXECUTION_TIME_MS", Float, nullable=True)
    DETAILS = Column("DETAILS", Text, nullable=True)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)


# ─── 12. AUDIT LOGS TABLE (Backward Compatibility) ───────────────────────────
class AuditLog(Base):
    __tablename__ = "AUDIT_LOGS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    ACTION_TYPE = Column("ACTION_TYPE", String, nullable=False)
    USER_ID = Column("USER_ID", String, nullable=False)
    ACTION_DETAILS = Column("ACTION_DETAILS", Text, nullable=True)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)
