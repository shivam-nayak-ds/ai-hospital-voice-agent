from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


# ─── 1. DEPARTMENTS TABLE ─────────────────────────────────────────────────────
class Department(Base):
    __tablename__ = "DEPARTMENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, unique=True, index=True)
    DESCRIPTION = Column("DESCRIPTION", String, nullable=True)
    LOCATION = Column("LOCATION", String, nullable=True)
    HEAD_DOCTOR_ID = Column("HEAD_DOCTOR_ID", Integer, nullable=True)
    IS_DELETED = Column("IS_DELETED", Boolean, nullable=False, default=False, index=True)
    DELETED_AT = Column("DELETED_AT", DateTime, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    doctors = relationship("Doctor", back_populates="department", foreign_keys="Doctor.DEPARTMENT_ID", cascade="all, delete-orphan")


# ─── 2. DOCTORS TABLE ─────────────────────────────────────────────────────────
class Doctor(Base):
    __tablename__ = "DOCTORS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, index=True)
    SPECIALIZATION = Column("SPECIALIZATION", String, nullable=False, index=True)
    QUALIFICATION = Column("QUALIFICATION", String, nullable=True)
    NMC_REG_NO = Column("NMC_REG_NO", String, nullable=True)  # National Medical Commission Reg No
    EXPERIENCE_YEARS = Column("EXPERIENCE_YEARS", Integer, nullable=True)
    CONSULTATION_FEE = Column("CONSULTATION_FEE", Integer, nullable=True)
    LANGUAGES = Column("LANGUAGES", String, nullable=True)
    STATUS = Column("STATUS", String, nullable=False, default="Active")
    IS_ON_LEAVE = Column("IS_ON_LEAVE", Boolean, nullable=False, default=False)
    EMAIL = Column("EMAIL", String, nullable=True)
    PHONE = Column("PHONE", String, nullable=True)
    ROOM_NUMBER = Column("ROOM_NUMBER", String, nullable=True)
    DEPARTMENT_ID = Column("DEPARTMENT_ID", Integer, ForeignKey("DEPARTMENTS.ID"), nullable=False)
    IS_DELETED = Column("IS_DELETED", Boolean, nullable=False, default=False, index=True)
    DELETED_AT = Column("DELETED_AT", DateTime, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_doctors_name_spec', 'NAME', 'SPECIALIZATION'),
    )

    # Relationships
    department = relationship("Department", back_populates="doctors", foreign_keys=[DEPARTMENT_ID])
    schedules = relationship("DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
    leaves = relationship("DoctorLeave", back_populates="doctor", cascade="all, delete-orphan")


# ─── 3. DOCTOR SCHEDULES TABLE ────────────────────────────────────────────────
class DoctorSchedule(Base):
    __tablename__ = "DOCTOR_SCHEDULES"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    DAY_OF_WEEK = Column("DAY_OF_WEEK", String, nullable=False)
    START_TIME = Column("START_TIME", String, nullable=False)
    END_TIME = Column("END_TIME", String, nullable=False)
    SLOT_DURATION_MIN = Column("SLOT_DURATION_MIN", Integer, nullable=False, default=30)
    STATUS = Column("STATUS", String, nullable=False, default="Available")
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    doctor = relationship("Doctor", back_populates="schedules")


# ─── 4. DOCTOR LEAVES TABLE (NEW) ─────────────────────────────────────────────
class DoctorLeave(Base):
    __tablename__ = "DOCTOR_LEAVES"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    LEAVE_DATE = Column("LEAVE_DATE", Date, nullable=False, index=True)
    REASON = Column("REASON", String, nullable=True)
    APPROVED_BY = Column("APPROVED_BY", String, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    # Relationships
    doctor = relationship("Doctor", back_populates="leaves")


# ─── 5. PATIENTS TABLE ────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "PATIENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    UHID = Column("UHID", String, nullable=True, unique=True, index=True)  # Unique Hospital ID (LH-2024-001)
    MRN = Column("MRN", String, nullable=True, index=True)                 # Medical Record Number
    NAME = Column("NAME", String, nullable=False, index=True)
    DATE_OF_BIRTH = Column("DATE_OF_BIRTH", Date, nullable=True)
    GENDER = Column("GENDER", String, nullable=True)
    BLOOD_GROUP = Column("BLOOD_GROUP", String, nullable=True)
    PHONE = Column("PHONE", String, nullable=False, index=True)
    EMAIL = Column("EMAIL", String, nullable=True)
    ADDRESS = Column("ADDRESS", String, nullable=True)
    EMERGENCY_CONTACT = Column("EMERGENCY_CONTACT", String, nullable=True)
    EMERGENCY_CONTACT_NAME = Column("EMERGENCY_CONTACT_NAME", String, nullable=True)
    IS_DELETED = Column("IS_DELETED", Boolean, nullable=False, default=False, index=True)
    DELETED_AT = Column("DELETED_AT", DateTime, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    lab_reports = relationship("LabReport", back_populates="patient", cascade="all, delete-orphan")
    insurance_policies = relationship("PatientInsurance", back_populates="patient", cascade="all, delete-orphan")
    admissions = relationship("BedAdmission", back_populates="patient", cascade="all, delete-orphan")


# ─── 6. APPOINTMENTS TABLE ────────────────────────────────────────────────────
class Appointment(Base):
    __tablename__ = "APPOINTMENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_NAME = Column("PATIENT_NAME", String, nullable=False)
    DOCTOR_NAME = Column("DOCTOR_NAME", String, nullable=False)
    APPOINTMENT_TIME = Column("APPOINTMENT_TIME", String, nullable=False)
    APPOINTMENT_DATE = Column("APPOINTMENT_DATE", Date, default=func.current_date(), nullable=False)
    DURATION_MINUTES = Column("DURATION_MINUTES", Integer, nullable=False, default=30)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    TYPE = Column("TYPE", String, nullable=False, default="OPD")  # OPD, Emergency, Teleconsult
    TOKEN_NO = Column("TOKEN_NO", Integer, nullable=True)
    STATUS = Column("STATUS", String, nullable=False, default="Confirmed")
    CANCELLED_BY = Column("CANCELLED_BY", String, nullable=True)
    CANCELLATION_REASON = Column("CANCELLATION_REASON", Text, nullable=True)
    CANCELLED_AT = Column("CANCELLED_AT", DateTime, nullable=True)
    NOTES = Column("NOTES", Text, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('DOCTOR_ID', 'APPOINTMENT_TIME', 'APPOINTMENT_DATE', name='uq_doctor_slot'),
        Index('idx_appt_doctor_date', 'DOCTOR_ID', 'APPOINTMENT_DATE'),
        Index('idx_appt_status', 'STATUS'),
        Index('idx_appt_patient', 'PATIENT_ID'),
    )

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    prescription = relationship("Prescription", back_populates="appointment", uselist=False)


# ─── 7. PRESCRIPTIONS TABLE (NEW) ─────────────────────────────────────────────
class Prescription(Base):
    __tablename__ = "PRESCRIPTIONS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    APPOINTMENT_ID = Column("APPOINTMENT_ID", Integer, ForeignKey("APPOINTMENTS.ID"), nullable=False, unique=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    DIAGNOSIS = Column("DIAGNOSIS", Text, nullable=True)
    MEDICATIONS_JSON = Column("MEDICATIONS_JSON", Text, nullable=True)  # JSON array of meds, dosages, frequency
    INSTRUCTIONS = Column("INSTRUCTIONS", Text, nullable=True)
    FOLLOW_UP_DATE = Column("FOLLOW_UP_DATE", Date, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    # Relationships
    appointment = relationship("Appointment", back_populates="prescription")
    patient = relationship("Patient")
    doctor = relationship("Doctor")


# ─── 8. BILLING CATALOG TABLE ──────────────────────────────────────────────────
class BillingCatalog(Base):
    __tablename__ = "BILLING_CATALOG"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    ITEM_NAME = Column("ITEM_NAME", String, nullable=False, index=True)
    CATEGORY = Column("CATEGORY", String, nullable=False)
    PRICE = Column("PRICE", Integer, nullable=False)
    CODE = Column("CODE", String, nullable=False, unique=True, index=True)
    IS_ACTIVE = Column("IS_ACTIVE", Boolean, nullable=False, default=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# ─── 9. INSURANCE PROVIDERS TABLE ──────────────────────────────────────────────
class InsuranceProvider(Base):
    __tablename__ = "INSURANCE_PROVIDERS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    NAME = Column("NAME", String, nullable=False, unique=True, index=True)
    TPA_CODE = Column("TPA_CODE", String, nullable=True, index=True)
    CASHLESS_AVAILABLE = Column("CASHLESS_AVAILABLE", Boolean, default=True, nullable=False)
    HELPLINE = Column("HELPLINE", String, nullable=True)
    IS_ACTIVE = Column("IS_ACTIVE", Boolean, nullable=False, default=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# ─── 10. PATIENT INSURANCE POLICIES TABLE (NEW) ───────────────────────────────
class PatientInsurance(Base):
    __tablename__ = "PATIENT_INSURANCE"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    PROVIDER_ID = Column("PROVIDER_ID", Integer, ForeignKey("INSURANCE_PROVIDERS.ID"), nullable=False)
    POLICY_NUMBER = Column("POLICY_NUMBER", String, nullable=False, index=True)
    MEMBER_ID = Column("MEMBER_ID", String, nullable=True)
    SUM_INSURED = Column("SUM_INSURED", Integer, nullable=True)
    VALID_TILL = Column("VALID_TILL", Date, nullable=True)
    STATUS = Column("STATUS", String, default="Active")
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="insurance_policies")
    provider = relationship("InsuranceProvider")


# ─── 11. WARD MANAGEMENT TABLE ─────────────────────────────────────────────────
class WardManagement(Base):
    __tablename__ = "WARD_MANAGEMENT"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    WARD_TYPE = Column("WARD_TYPE", String, nullable=False, unique=True, index=True)
    TOTAL_BEDS = Column("TOTAL_BEDS", Integer, nullable=False)
    OCCUPIED_BEDS = Column("OCCUPIED_BEDS", Integer, nullable=False, default=0)
    PRICE_PER_DAY = Column("PRICE_PER_DAY", Integer, nullable=False)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint('"OCCUPIED_BEDS" >= 0', name='chk_occupied_beds_positive'),
        CheckConstraint('"OCCUPIED_BEDS" <= "TOTAL_BEDS"', name='chk_occupied_beds_limit'),
    )

    # Relationships
    beds = relationship("Bed", back_populates="ward_category", cascade="all, delete-orphan")


# ─── 12. INDIVIDUAL BEDS TABLE (NEW) ──────────────────────────────────────────
class Bed(Base):
    __tablename__ = "BEDS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    BED_NUMBER = Column("BED_NUMBER", String, nullable=False, unique=True, index=True)  # e.g., 'G-101', 'ICU-05'
    WARD_ID = Column("WARD_ID", Integer, ForeignKey("WARD_MANAGEMENT.ID"), nullable=False)
    FLOOR = Column("FLOOR", Integer, default=1)
    STATUS = Column("STATUS", String, default="Available")  # Available, Occupied, Maintenance, Cleaning
    IS_ACTIVE = Column("IS_ACTIVE", Boolean, default=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    # Relationships
    ward_category = relationship("WardManagement", back_populates="beds")
    admissions = relationship("BedAdmission", back_populates="bed")


# ─── 13. BED ADMISSIONS TABLE (NEW) ───────────────────────────────────────────
class BedAdmission(Base):
    __tablename__ = "BED_ADMISSIONS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    BED_ID = Column("BED_ID", Integer, ForeignKey("BEDS.ID"), nullable=False)
    ADMITTED_DOCTOR_ID = Column("ADMITTED_DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    ADMISSION_DATE = Column("ADMISSION_DATE", DateTime, default=func.now(), nullable=False)
    DISCHARGE_DATE = Column("DISCHARGE_DATE", DateTime, nullable=True)
    STATUS = Column("STATUS", String, default="Admitted")  # Admitted, Discharged, Transferred
    ADMISSION_NOTES = Column("ADMISSION_NOTES", Text, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="admissions")
    bed = relationship("Bed", back_populates="admissions")
    admitting_doctor = relationship("Doctor")


# ─── 14. OPD TOKENS QUEUE TABLE (NEW) ─────────────────────────────────────────
class OPDToken(Base):
    __tablename__ = "OPD_TOKENS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    DOCTOR_ID = Column("DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    TOKEN_NUMBER = Column("TOKEN_NUMBER", Integer, nullable=False)
    DATE = Column("DATE", Date, default=func.current_date(), nullable=False)
    PATIENT_NAME = Column("PATIENT_NAME", String, nullable=False)
    PHONE = Column("PHONE", String, nullable=False)
    STATUS = Column("STATUS", String, default="Waiting")  # Waiting, With Doctor, Completed, Skipped
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('DOCTOR_ID', 'TOKEN_NUMBER', 'DATE', name='uq_doctor_daily_token'),
        Index('idx_opd_token_doc_date', 'DOCTOR_ID', 'DATE'),
    )


# ─── 15. LAB REPORTS TABLE ─────────────────────────────────────────────────────
class LabReport(Base):
    __tablename__ = "LAB_REPORTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    ORDERED_BY_DOCTOR_ID = Column("ORDERED_BY_DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=True)
    TEST_NAME = Column("TEST_NAME", String, nullable=False, index=True)
    RESULT = Column("RESULT", String, nullable=True)
    NORMAL_RANGE = Column("NORMAL_RANGE", String, nullable=True)
    STATUS = Column("STATUS", String, nullable=False, default="Pending")
    ORDERED_DATE = Column("ORDERED_DATE", Date, default=func.current_date(), nullable=False)
    COMPLETED_DATE = Column("COMPLETED_DATE", DateTime, nullable=True)
    REPORT_URL = Column("REPORT_URL", String, nullable=True)
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)
    UPDATED_AT = Column("UPDATED_AT", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="lab_reports")
    ordered_by_doctor = relationship("Doctor")


# ─── 16. NOTIFICATIONS AUDIT TABLE (NEW) ──────────────────────────────────────
class NotificationLog(Base):
    __tablename__ = "NOTIFICATIONS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    RECIPIENT = Column("RECIPIENT", String, nullable=False, index=True)  # Phone or Email
    CHANNEL = Column("CHANNEL", String, nullable=False)                 # SMS, WhatsApp, Email
    EVENT_TYPE = Column("EVENT_TYPE", String, nullable=False)           # OTP, Booking_Confirm, Discharge
    MESSAGE_BODY = Column("MESSAGE_BODY", Text, nullable=False)
    STATUS = Column("STATUS", String, default="Sent")                   # Sent, Delivered, Failed
    PROVIDER_MESSAGE_ID = Column("PROVIDER_MESSAGE_ID", String, nullable=True)
    SENT_AT = Column("SENT_AT", DateTime, default=func.now(), nullable=False)


# ─── 17. DOCTOR REFERRALS TABLE (NEW) ─────────────────────────────────────────
class DoctorReferral(Base):
    __tablename__ = "REFERRALS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    PATIENT_ID = Column("PATIENT_ID", Integer, ForeignKey("PATIENTS.ID"), nullable=False)
    FROM_DOCTOR_ID = Column("FROM_DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    TO_DOCTOR_ID = Column("TO_DOCTOR_ID", Integer, ForeignKey("DOCTORS.ID"), nullable=False)
    REFERRAL_REASON = Column("REFERRAL_REASON", Text, nullable=True)
    STATUS = Column("STATUS", String, default="Pending")  # Pending, Consulted
    CREATED_AT = Column("CREATED_AT", DateTime, default=func.now(), nullable=False)


# ─── 18. CONVERSATION LOGS TABLE ──────────────────────────────────────────────
class ConversationLog(Base):
    __tablename__ = "CONVERSATION_LOGS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    SESSION_ID = Column("SESSION_ID", String, nullable=False, index=True)
    ROLE = Column("ROLE", String, nullable=False)
    CONTENT = Column("CONTENT", Text, nullable=False)
    INTENT = Column("INTENT", String, nullable=True)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)


# ─── 19. AGENT EVENTS TABLE ───────────────────────────────────────────────────
class AgentEvent(Base):
    __tablename__ = "AGENT_EVENTS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    SESSION_ID = Column("SESSION_ID", String, nullable=False, index=True)
    EVENT_TYPE = Column("EVENT_TYPE", String, nullable=False, index=True)
    ROUTER_NAME = Column("ROUTER_NAME", String, nullable=True)
    EXECUTION_TIME_MS = Column("EXECUTION_TIME_MS", Float, nullable=True)
    DETAILS = Column("DETAILS", Text, nullable=True)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)


# ─── 20. AUDIT LOGS TABLE ─────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "AUDIT_LOGS"

    ID = Column("ID", Integer, primary_key=True, autoincrement=True)
    ACTION_TYPE = Column("ACTION_TYPE", String, nullable=False, index=True)
    USER_ID = Column("USER_ID", String, nullable=False)
    ACTION_DETAILS = Column("ACTION_DETAILS", Text, nullable=True)
    IP_ADDRESS = Column("IP_ADDRESS", String, nullable=True)
    TIMESTAMP = Column("TIMESTAMP", DateTime, default=func.now(), nullable=False)
