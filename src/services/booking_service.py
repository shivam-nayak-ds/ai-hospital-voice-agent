from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.doctor_repository import DoctorRepository
from src.repositories.patient_repository import PatientRepository
from src.schemas.appointment import SlotCheckSchema, AppointmentBookSchema, AppointmentCancelSchema
from src.core.domain_exceptions import (
    DoctorNotFoundError,
    SlotUnavailableError,
    ValidationError
)
from src.utils.logger import custom_logger as logger

class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.appointment_repo = AppointmentRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.patient_repo = PatientRepository(db)

    async def check_slot_availability(self, doctor_name: str, date_str: str, time_str: str) -> str:
        """
        Validates input schema, resolves canonical doctor name, and checks slot availability.
        """
        try:
            schema = SlotCheckSchema(
                doctor_name=doctor_name,
                appointment_date=date_str,
                appointment_time=time_str
            )
        except Exception as e:
            raise ValidationError(field="appointment_parameters", message=str(e))

        date_obj = datetime.strptime(schema.appointment_date, "%Y-%m-%d").date()

        # Resolve doctor
        doctors = await self.doctor_repo.get_by_name_substring(schema.doctor_name)
        if not doctors:
            raise DoctorNotFoundError(doctor_name=schema.doctor_name)
        
        if len(doctors) > 1:
            names = ", ".join([f"Dr. {d.NAME}" for d in doctors])
            raise ValidationError(
                field="doctor_name",
                message=f"Multiple doctors found matching '{schema.doctor_name}': {names}. Please specify the full name."
            )
        
        doctor = doctors[0]

        existing = await self.appointment_repo.check_slot_conflict(
            doctor_id=doctor.ID,
            appt_date=date_obj,
            appt_time=schema.appointment_time,
            lock=False
        )

        if existing:
            return f"Slot {schema.appointment_time} on {schema.appointment_date} with Dr. {doctor.NAME} is already booked."
        return f"Slot {schema.appointment_time} on {schema.appointment_date} with Dr. {doctor.NAME} is available."

    async def book_appointment(self, patient_name: str, patient_phone: str, doctor_name: str, date_str: str, time_str: str) -> str:
        """
        Concurrently safe appointment booking using pessimistic locking (FOR UPDATE) and unique constraint fallback.
        """
        try:
            schema = AppointmentBookSchema(
                doctor_name=doctor_name,
                appointment_date=date_str,
                appointment_time=time_str,
                patient_name=patient_name,
                patient_phone=patient_phone
            )
        except Exception as e:
            raise ValidationError(field="booking_parameters", message=str(e))

        date_obj = datetime.strptime(schema.appointment_date, "%Y-%m-%d").date()

        # 1. Resolve canonical doctor
        doctors = await self.doctor_repo.get_by_name_substring(schema.doctor_name)
        if not doctors:
            raise DoctorNotFoundError(doctor_name=schema.doctor_name)
        
        if len(doctors) > 1:
            names = ", ".join([f"Dr. {d.NAME}" for d in doctors])
            raise ValidationError(
                field="doctor_name",
                message=f"Multiple doctors found matching '{schema.doctor_name}': {names}. Please specify the full name."
            )
        
        doctor = doctors[0]

        # 2. Resolve/Create Patient record
        patient = await self.patient_repo.get_by_phone(schema.patient_phone)
        if not patient:
            patient = await self.patient_repo.create(name=schema.patient_name, phone=schema.patient_phone)

        # 3. Pessimistic lock row check
        existing = await self.appointment_repo.check_slot_conflict(
            doctor_id=doctor.ID,
            appt_date=date_obj,
            appt_time=schema.appointment_time,
            lock=True
        )

        if existing:
            raise SlotUnavailableError(
                doctor=doctor.NAME,
                date_str=schema.appointment_date,
                time_str=schema.appointment_time
            )

        try:
            # 4. Create appointment record
            appt = await self.appointment_repo.create(
                patient_id=patient.ID,
                patient_name=patient.NAME,
                doctor_id=doctor.ID,
                doctor_name=doctor.NAME,
                appt_date=date_obj,
                appt_time=schema.appointment_time
            )
            logger.info(f"Booked Appointment ID {appt.ID}: {patient.NAME} with Dr. {doctor.NAME}")
            
            # Resolve department location for address info
            from src.db.models import Department
            from sqlalchemy import select
            location = "Main Clinic"
            if doctor.DEPARTMENT_ID:
                stmt = select(Department.LOCATION).where(Department.ID == doctor.DEPARTMENT_ID)
                loc_result = await self.db.execute(stmt)
                loc_val = loc_result.scalar_one_or_none()
                if loc_val:
                    location = loc_val

            # Trigger Asynchronous Notification (Phase 5/6 Email + PDF Attachment)
            if patient.EMAIL:
                from src.services.notification_service import NotificationService
                await NotificationService.send_booking_email(
                    to_email=patient.EMAIL,
                    patient_name=patient.NAME,
                    doctor_name=doctor.NAME,
                    date_str=schema.appointment_date,
                    time_str=schema.appointment_time,
                    location=location,
                    appointment_id=appt.ID
                )

            return (
                f"Appointment confirmed! ID: {appt.ID} | Patient: {patient.NAME} | "
                f"Doctor: Dr. {doctor.NAME} ({doctor.SPECIALIZATION}) | "
                f"Date: {schema.appointment_date} | Time: {schema.appointment_time} | "
                f"Location: {location}. "
                f"Please arrive 15 minutes early."
            )
        except Exception as e:
            if "uq_doctor_slot" in str(e).lower() or "unique" in str(e).lower():
                raise SlotUnavailableError(
                    doctor=doctor.NAME,
                    date_str=schema.appointment_date,
                    time_str=schema.appointment_time
                )
            raise e

    async def cancel_appointment(self, appointment_id: int) -> str:
        """
        Cancels an existing appointment.
        """
        try:
            schema = AppointmentCancelSchema(appointment_id=appointment_id)
        except Exception as e:
            raise ValidationError(field="appointment_id", message=str(e))

        appt = await self.appointment_repo.get_by_id(schema.appointment_id)
        if not appt:
            return f"No appointment found with ID {schema.appointment_id}."
        if appt.STATUS == "Cancelled":
            return f"Appointment ID {schema.appointment_id} is already cancelled."

        await self.appointment_repo.cancel(appt)

        # Trigger Cancellation Notification (Phase 5 Email)
        try:
            patient = await self.patient_repo.get_by_id(appt.PATIENT_ID)
            if patient and patient.EMAIL:
                from src.services.notification_service import NotificationService
                await NotificationService.send_cancellation_email(
                    to_email=patient.EMAIL,
                    patient_name=patient.NAME,
                    doctor_name=appt.DOCTOR_NAME,
                    date_str=str(appt.APPOINTMENT_DATE),
                    time_str=appt.APPOINTMENT_TIME,
                    appointment_id=appt.ID
                )
        except Exception as ex:
            logger.error(f"Failed to trigger cancellation notification: {ex}")

        return (
            f"Appointment ID {schema.appointment_id} with Dr. {appt.DOCTOR_NAME} on {appt.APPOINTMENT_DATE} "
            f"at {appt.APPOINTMENT_TIME} has been cancelled successfully."
        )
