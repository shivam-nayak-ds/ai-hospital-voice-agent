
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain_exceptions import PatientNotFoundError, ValidationError
from src.db.models import LabReport, Patient
from src.repositories.lab_repository import LabRepository
from src.repositories.patient_repository import PatientRepository
from src.schemas.lab import LabReportQuerySchema


class LabService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.lab_repo = LabRepository(db)
        self.patient_repo = PatientRepository(db)

    async def get_patient_reports(self, patient_phone: str) -> tuple[list[LabReport], Patient]:
        """
        Retrieves all lab reports ordered for a patient matching the phone number.
        """
        try:
            schema = LabReportQuerySchema(patient_phone=patient_phone)
        except Exception as e:
            raise ValidationError(field="patient_phone", message=str(e))

        patient = await self.patient_repo.get_by_phone(schema.patient_phone)
        if not patient:
            raise PatientNotFoundError(identifier=f"phone ending in {schema.patient_phone[-4:]}")

        reports = await self.lab_repo.get_patient_reports(patient.ID)
        return reports, patient
