from typing import Optional
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Appointment

class AppointmentRepository:
    """
    Encapsulates database access operations for Appointment creation, lookup, and cancellation.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Fetches appointment details for the given appointment ID."""
        stmt = select(Appointment).filter(Appointment.ID == appointment_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def check_slot_conflict(self, doctor_id: int, appt_date: date, appt_time: str, lock: bool = False) -> Optional[Appointment]:
        """Verifies if a specific slot is already reserved for a doctor."""
        stmt = select(Appointment).filter(
            Appointment.DOCTOR_ID == doctor_id,
            Appointment.APPOINTMENT_DATE == appt_date,
            Appointment.APPOINTMENT_TIME == appt_time,
            Appointment.STATUS == "Confirmed"
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, patient_id: int, patient_name: str, doctor_id: int, doctor_name: str, appt_date: date, appt_time: str) -> Appointment:
        """Inserts a confirmed appointment slot."""
        appt = Appointment(
            PATIENT_ID=patient_id,
            PATIENT_NAME=patient_name,
            DOCTOR_ID=doctor_id,
            DOCTOR_NAME=doctor_name,
            APPOINTMENT_DATE=appt_date,
            APPOINTMENT_TIME=appt_time,
            STATUS="Confirmed"
        )
        self.db.add(appt)
        await self.db.flush()  # Populate appt.ID
        return appt

    async def cancel(self, appointment: Appointment) -> None:
        """Sets the status of an appointment to Cancelled and flushes to the DB session."""
        appointment.STATUS = "Cancelled"
        await self.db.flush()  # Persist the status change within the current transaction
