from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Patient

class PatientRepository:
    """
    Encapsulates database access operations for Patient profiles.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_phone(self, phone: str) -> Optional[Patient]:
        """Fetches a patient record matching the exact phone number."""
        stmt = select(Patient).filter(Patient.PHONE == phone)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """Fetches a patient record matching the exact primary key ID."""
        stmt = select(Patient).filter(Patient.ID == patient_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, name: str, phone: str) -> Patient:
        """Registers a new patient profile in the database."""
        patient = Patient(NAME=name, PHONE=phone)
        self.db.add(patient)
        await self.db.flush()  # Populate patient.ID
        return patient

