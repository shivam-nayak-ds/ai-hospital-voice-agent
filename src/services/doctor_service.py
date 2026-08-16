
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain_exceptions import DoctorNotFoundError, ValidationError
from src.db.models import Doctor, DoctorSchedule
from src.repositories.doctor_repository import DoctorRepository


class DoctorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doctor_repo = DoctorRepository(db)

    async def search_doctors_by_specialty(self, specialization: str) -> list[Doctor]:
        """
        Retrieves active doctors matching a specialization query.
        """
        if not specialization or len(specialization.strip()) < 2:
            raise ValidationError(
                field="specialization",
                message="Please specify a valid specialty (e.g., Cardiology, Pediatrics)."
            )
        return await self.doctor_repo.search_by_specialty(specialization)

    async def get_doctor_schedule(self, doctor_name: str) -> tuple[list[DoctorSchedule], Doctor]:
        """
        Retrieves schedule details for a single resolved active doctor.
        """
        if not doctor_name or len(doctor_name.strip()) < 2:
            raise ValidationError(
                field="doctor_name",
                message="Please specify a valid doctor name."
            )
        
        matching_doctors = await self.doctor_repo.get_by_name_substring(doctor_name)
        if not matching_doctors:
            raise DoctorNotFoundError(doctor_name=doctor_name)

        if len(matching_doctors) > 1:
            names = ", ".join([f"Dr. {d.NAME}" for d in matching_doctors])
            raise ValidationError(
                field="doctor_name",
                message=f"Multiple doctors found matching '{doctor_name}': {names}. Please specify the full name."
            )

        doctor = matching_doctors[0]
        schedules = await self.doctor_repo.get_schedules(doctor.ID)
        return schedules, doctor
